import io
import json
import uuid
import zipfile

from libpebble2.util.bundle import PebbleBundle
from libpebble2.util.hardware import PebbleHardware


def make_bundle_bytes(platform_prefix="", sdk_minor=0x10):
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        # Minimal app binary header following STRUCT_DEFINITION sizes
        # We'll construct fields to satisfy get_app_metadata
        header = b"PebblePBL"  # header(8s)
        header += bytes([1, 0])  # struct version
        header += bytes([0, sdk_minor])  # sdk version
        header += bytes([1, 2])  # app version major/minor
        header += (0).to_bytes(2, "big")  # size
        header += (0).to_bytes(4, "big")  # offset
        header += (0).to_bytes(4, "big")  # crc
        header += b"App\x00".ljust(32, b"\x00")  # app_name
        header += b"Co\x00".ljust(32, b"\x00")  # company_name
        header += (0).to_bytes(4, "big")  # icon resource id
        header += (0).to_bytes(4, "big")  # sym table addr
        header += (0).to_bytes(4, "big")  # flags
        header += (0).to_bytes(4, "big")  # relocation count
        header += uuid.UUID("01234567-89ab-4cde-8123-456789abcdef").bytes  # uuid
        app_bin = header + b"\x00\x00"  # some payload

        manifest = {
            "application": {"name": "app.bin"},
        }
        z.writestr(platform_prefix + "manifest.json", json.dumps(manifest))
        z.writestr(platform_prefix + "app.bin", app_bin)
    zbuf.seek(0)
    return zbuf.getvalue()


def test_bundle_should_permit_install_by_platform(tmp_path):
    b = tmp_path / "x.pbw"
    b.write_bytes(make_bundle_bytes(platform_prefix="basalt/"))
    pb = PebbleBundle(str(b), hardware=PebbleHardware.SNOWY_DVT)  # basalt
    assert pb.should_permit_install() is True
    md = pb.get_app_metadata()
    assert md["app_name"].strip("\x00") == "App"
    pb.close()
