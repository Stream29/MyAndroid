"""Offline unit and sanitization tests for MyAndroid Play Integrity tooling and templates."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.machinery
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bin" / "play-integrity"
TEMPLATES_DIR = REPO_ROOT / "templates" / "play-integrity"


def _load_play_integrity_module():
    loader = importlib.machinery.SourceFileLoader("play_integrity_mod", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("play_integrity_mod", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["play_integrity_mod"] = module
    loader.exec_module(module)
    return module


PI = _load_play_integrity_module()


def _make_synthetic_keybox_xml(*, days: int, backdate_expired: bool = False) -> str:
    """Generate a temporary self-signed ECDSA keybox XML strictly for unit testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        key_path = tmp / "test.key"
        cert1_path = tmp / "cert1.pem"
        cert2_path = tmp / "cert2.pem"

        subprocess.run(
            ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(key_path)],
            check=True,
            capture_output=True,
        )
        # Keep cert PEMs without embedding private key material into assertions.
        if backdate_expired:
            # Generate an already-expired cert using explicit start/end dates via openssl ca/x509 faketime-free check:
            # openssl x509 -days 1 produces valid for 1 day; tests pass `now` after expiry to verify detection.
            pass
        for out_path, cn in ((cert1_path, "TEE-Leaf"), (cert2_path, "TEE-Root")):
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-new",
                    "-x509",
                    "-key",
                    str(key_path),
                    "-out",
                    str(out_path),
                    "-days",
                    str(days),
                    "-subj",
                    f"/CN={cn}",
                ],
                check=True,
                capture_output=True,
            )
        c1 = cert1_path.read_text(encoding="utf-8").strip()
        c2 = cert2_path.read_text(encoding="utf-8").strip()
        return f"""<?xml version="1.0"?>
<AndroidAttestation>
  <NumberOfKeyboxes>1</NumberOfKeyboxes>
  <Keybox DeviceID="synthetic-test">
    <Key algorithm="ecdsa">
      <PrivateKey format="pem">SYNTHETIC-TEST-PLACEHOLDER</PrivateKey>
      <CertificateChain>
        <NumberOfCertificates>2</NumberOfCertificates>
        <Certificate format="pem">
{c1}
        </Certificate>
        <Certificate format="pem">
{c2}
        </Certificate>
      </CertificateChain>
    </Key>
  </Keybox>
</AndroidAttestation>
"""


def _healthy_snapshot(keybox_xml: str):
    return PI.DeviceSnapshot(
        serial="TESTSERIAL",
        marketname="Test Phone",
        model="TestModel",
        device="testdev",
        android_release="16",
        sdk_int="36",
        incremental="OS3.0.0",
        verified_boot_state="green",
        flash_locked="1",
        vbmeta_state="locked",
        live_security_patch="2026-11-05",
        live_vendor_patch="2026-11-05",
        modules={
            "hybrid_mount": {"id": "hybrid_mount", "name": "Hybrid Mount", "version": "6.2.6", "enabled": "true"},
            "zygisksu": {"id": "zygisksu", "name": "Zygisk Next", "version": "1.5.2", "enabled": "true"},
            "playintegrityfix": {"id": "playintegrityfix", "name": "PIF", "version": "v4.9-inject-s", "enabled": "true"},
            "tricky_store": {"id": "tricky_store", "name": "TEESimulator-RS", "version": "v6.0.1-307", "enabled": "true"},
            "hma_oss_zygisk": {"id": "hma_oss_zygisk", "name": "HMA-OSS", "version": "zygisk", "enabled": "true"},
        },
        tricky_module_files=("classes.dex", "daemon", "inject", "libTEESimulator.so", "libcertgen.so", "supervisor"),
        running_daemons="root 1996 1 supervisor ./daemon /data/adb/modules/tricky_store",
        data_pif_text="\n".join(
            [
                "FINGERPRINT=google/cubs_beta/cubs:CANARY/ZP11.261016.008/16754936:user/release-keys",
                "MANUFACTURER=Google",
                "MODEL=Pixel 11",
                "SECURITY_PATCH=2026-11-05",
                "DEVICE_INITIAL_SDK_INT=37",
                "spoofBuild=true",
                "spoofProps=true",
                "spoofProvider=false",
                "spoofSignature=false",
                "spoofVendingBuild=true",
                "spoofVendingSdk=false",
                "DEBUG=false",
            ]
        ),
        pif_system_prop_text="ro.build.version.security_patch=2026-11-05\nro.vendor.build.security_patch=2026-11-05\n",
        has_auto_security_patch=True,
        security_patch_txt="system=202611\nboot=2026-11-05\nvendor=2026-11-05\n",
        keybox_xml=keybox_xml,
        hbk_size=32,
        boot_hash_size=32,
        boot_key_size=32,
        tee_status="teeBroken=false",
        target_txt="com.google.android.gms!\ncom.android.vending!\ncom.google.android.gsf!\ngr.nikolasspyr.integritycheck!\n",
        checker_installed=True,
        gms_version="26.44.32",
        vending_version="50.2.11-24",
    )


@unittest.skipUnless(shutil.which("openssl"), "openssl is required for X.509 tests")
class PlayIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.valid_keybox = _make_synthetic_keybox_xml(days=365)

    def test_healthy_snapshot_passes_without_warnings_or_failures(self) -> None:
        snap = _healthy_snapshot(self.valid_keybox)
        ok, warn, fail = PI.evaluate_device_snapshot(snap)
        self.assertEqual(fail, [])
        self.assertEqual(warn, [])
        self.assertTrue(any("TEESimulator-RS" in line for line in ok))
        self.assertTrue(any("Security patch aligned" in line for line in ok))

    def test_legacy_service_apk_and_spoof_props_false_and_patch_mismatch_fail(self) -> None:
        base = _healthy_snapshot(self.valid_keybox)
        broken = PI.DeviceSnapshot(
            **{
                **base.__dict__,
                "tricky_module_files": ("daemon", "libtricky_store.so", "service.apk"),
                "data_pif_text": base.data_pif_text.replace("spoofProps=true", "spoofProps=false"),
                "security_patch_txt": "system=202605\nboot=2026-05-05\nvendor=2026-05-05\n",
                "target_txt": "com.google.android.gms\ncom.android.vending!\n",
            }
        )
        _, _, fail = PI.evaluate_device_snapshot(broken)
        joined = "\n".join(fail)
        self.assertIn("Legacy TrickyStore (service.apk)", joined)
        self.assertIn("spoofProps=false", joined)
        self.assertIn("Security patch mismatch", joined)
        self.assertIn("target.txt missing '!'", joined)

    def test_expired_keybox_detected(self) -> None:
        snap = _healthy_snapshot(_make_synthetic_keybox_xml(days=1))
        future_now = datetime(2099, 1, 1, tzinfo=timezone.utc)
        _, _, fail = PI.evaluate_device_snapshot(snap, now=future_now)
        self.assertTrue(any("invalid certificate window" in line for line in fail))

    def test_patch_pif_flags_and_normalize_targets(self) -> None:
        raw_pif = "FINGERPRINT=test/fp\nspoofBuild=false\nspoofProps=false\n"
        patched = PI.patch_pif_flags(
            raw_pif,
            {"spoofBuild": "true", "spoofProps": "true", "spoofVendingBuild": "true"},
        )
        kv = PI.parse_kv_lines(patched)
        self.assertEqual(kv["FINGERPRINT"], "test/fp")
        self.assertEqual(kv["spoofBuild"], "true")
        self.assertEqual(kv["spoofProps"], "true")
        self.assertEqual(kv["spoofVendingBuild"], "true")

        lines = [
            "# header comment",
            "com.google.android.gms",
            "com.google.android.gms!",
            "com.android.vending",
            "com.example.bank",
        ]
        updated, changes = PI.normalize_target_lines(
            lines,
            required_bang=("com.google.android.gms", "com.android.vending", "com.google.android.gsf"),
            optional_bang=("gr.nikolasspyr.integritycheck",),
        )
        self.assertEqual(
            updated,
            [
                "# header comment",
                "com.google.android.gms!",
                "com.android.vending!",
                "com.example.bank",
                "com.google.android.gsf!",
                "gr.nikolasspyr.integritycheck!",
            ],
        )
        self.assertTrue(changes)

    def test_templates_and_public_repo_sanitized(self) -> None:
        pif_example = PI.parse_kv_lines((TEMPLATES_DIR / "pif.prop.example").read_text(encoding="utf-8"))
        self.assertEqual(pif_example["spoofBuild"], "true")
        self.assertEqual(pif_example["spoofProps"], "true")
        self.assertEqual(pif_example["spoofVendingBuild"], "true")

        sec_example = PI.parse_kv_lines((TEMPLATES_DIR / "security_patch.txt.example").read_text(encoding="utf-8"))
        self.assertEqual(set(sec_example.keys()), {"system", "boot", "vendor"})

        baseline = (TEMPLATES_DIR / "target.txt.baseline").read_text(encoding="utf-8")
        for pkg in ("com.google.android.gms!", "com.android.vending!", "com.google.android.gsf!"):
            self.assertIn(pkg, baseline)

        global_forbidden = (
            "BEGIN EC PRIVATE KEY",
            "BEGIN RSA PRIVATE KEY",
            "BEGIN PRIVATE KEY",
            "6TMBIJDIM799NFQC",
            "f22d560b",
            "@gmail.com",
            "@qq.com",
        )
        for root_dir in (REPO_ROOT / "bin", REPO_ROOT / "docs", REPO_ROOT / "templates"):
            for file_path in root_dir.rglob("*"):
                if not file_path.is_file() or "__pycache__" in file_path.parts:
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for marker in global_forbidden:
                    self.assertFalse(
                        marker in content,
                        f"Sensitive marker {marker!r} leaked into {file_path}",
                    )

        personal_target_markers = ("cmb.pb", "cn.gov.tax.its", "com.cl.newt66y", "com.okinc.okex.gp")
        for root_dir in (REPO_ROOT / "bin", REPO_ROOT / "docs", REPO_ROOT / "templates"):
            for file_path in root_dir.rglob("*"):
                if not file_path.is_file() or "__pycache__" in file_path.parts:
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for marker in personal_target_markers:
                    self.assertFalse(
                        marker in content,
                        f"Personal app marker {marker!r} leaked into {file_path}",
                    )

    def test_cmd_backup_and_ensure_targets_with_fake_device(self) -> None:
        class FakeDevice:
            def __init__(self) -> None:
                self.serial = "FAKE123"
                self.files = {
                    f"{PI.TARGET_DATA_TRICKY}/keybox.xml": b"<AndroidAttestation/>",
                    f"{PI.TARGET_DATA_TRICKY}/hbk": b"x" * 32,
                    f"{PI.TARGET_DATA_PIF}": b"FINGERPRINT=fake\n",
                    f"{PI.TARGET_DATA_TRICKY}/target.txt": b"com.google.android.gms\ncom.example.app\n",
                    f"{PI.TARGET_LSPD_DB}": b"sqlite-fake",
                    f"{PI.TARGET_HYPERCEILER_PREFS}": b"<map/>",
                    f"{PI.TARGET_KSU_ALLOWLIST}": b"ksu-bin",
                }
                self.pushed: dict[str, tuple[bytes, str]] = {}

            def shell(self, script: str, *, check: bool = True, timeout: int = 20) -> str:
                if "getprop ro.product.device" in script:
                    return "fakedev"
                if "pm path" in script:
                    return "1"
                return ""

            def pull_root_bytes(self, remote_path: str, *, timeout: int = 20) -> bytes | None:
                return self.files.get(remote_path)

            def push_root_bytes(self, data: bytes, remote_path: str, mode: str = "0644") -> None:
                self.pushed[remote_path] = (data, mode)
                self.files[remote_path] = data

        dev = FakeDevice()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "backup"
            rc = PI.cmd_backup(
                [dev],
                type("Args", (), {"out_dir": out_dir, "include_hma": False, "include_root_configs": True})(),
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual((out_dir / "keybox.xml").stat().st_mode & 0o777, 0o600)
            self.assertEqual((out_dir / "hbk").read_bytes(), b"x" * 32)
            self.assertEqual((out_dir / "lspd-modules_config.db").read_bytes(), b"sqlite-fake")
            self.assertEqual((out_dir / "hyperceiler_prefs.xml").read_bytes(), b"<map/>")
            self.assertEqual((out_dir / "ksu-allowlist.bin").read_bytes(), b"ksu-bin")
            self.assertEqual((out_dir / "ksu-allowlist.bin").stat().st_mode & 0o777, 0o600)

        rc_dry = PI.cmd_ensure_targets([dev], type("Args", (), {"dry_run": True})())
        self.assertEqual(rc_dry, 0)
        self.assertEqual(dev.pushed, {})

        rc_apply = PI.cmd_ensure_targets([dev], type("Args", (), {"dry_run": False})())
        self.assertEqual(rc_apply, 0)
        target_written = dev.pushed[f"{PI.TARGET_DATA_TRICKY}/target.txt"][0].decode("utf-8").splitlines()
        self.assertEqual(
            target_written,
            [
                "com.google.android.gms!",
                "com.example.app",
                "com.android.vending!",
                "com.google.android.gsf!",
                "gr.nikolasspyr.integritycheck!",
            ],
        )


if __name__ == "__main__":
    unittest.main()
