"""Generate the inert Android-shaped ZIP used by the scan demo."""

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile


if __name__ == "__main__":
    output = Path(__file__).with_name("Shaadi_Card_Priya.pdf.apk")
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("AndroidManifest.xml", "This is a harmless test file for the Card Kholo demo")
        archive.writestr("classes.dex", b"")
    output.write_bytes(buffer.getvalue())
    print(output.name)
