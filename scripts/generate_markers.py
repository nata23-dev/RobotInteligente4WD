"""Genera PDF A4 vectorial a escala real; dependencia opcional reportlab."""

from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def generate(target=ROOT / "docs" / "recursos" / "estaciones_aruco.pdf"):
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(target), pagesize=(210 * mm, 297 * mm))
    pdf.setTitle("Robot Inteligente 4WD - Estaciones ArUco")
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary)
    for identity, name in enumerate(["Cubos", "Cilindros", "Prismas triangulares"]):
        pattern = cv2.aruco.generateImageMarker(dictionary, identity, 6)
        raster = cv2.copyMakeBorder(
            cv2.resize(pattern, (600, 600), interpolation=cv2.INTER_NEAREST),
            120,
            120,
            120,
            120,
            cv2.BORDER_CONSTANT,
            value=255,
        )
        _, ids, _ = detector.detectMarkers(raster)
        if ids is None or ids.flatten().tolist() != [identity]:
            raise RuntimeError("Marcador digital inválido")
        pdf.setFillColorRGB(0.14, 0.20, 0.28)
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawCentredString(105 * mm, 264 * mm, name)
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(
            105 * mm, 252 * mm, f"Estacion ID {identity} - DICT_4X4_50"
        )
        # Patrón de 100 mm: 6 módulos (4 datos + dos bordes).
        left, bottom, side = 55 * mm, 120 * mm, 100 * mm
        pdf.setFillColorRGB(0, 0, 0)
        for row in range(6):
            for col in range(6):
                if pattern[row, col] == 0:
                    pdf.rect(
                        left + col * side / 6,
                        bottom + (5 - row) * side / 6,
                        side / 6 + 0.01,
                        side / 6 + 0.01,
                        fill=1,
                        stroke=0,
                    )
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(
            105 * mm, 101 * mm, "Patron: 100 x 100 mm. Margen blanco: al menos 20 mm."
        )
        pdf.drawCentredString(
            105 * mm, 92 * mm, "Imprimir al 100 %, sin ajustar ni escalar a pagina."
        )
        pdf.drawCentredString(
            105 * mm,
            83 * mm,
            "Propuesta inicial: verificar tamano y deteccion con camara real.",
        )
        pdf.setLineWidth(0.5)
        pdf.line(55 * mm, 63 * mm, 155 * mm, 63 * mm)
        for x in (55, 155):
            pdf.line(x * mm, 61 * mm, x * mm, 65 * mm)
        pdf.drawCentredString(105 * mm, 55 * mm, "Referencia de escala: 100 mm")
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(
            105 * mm,
            22 * mm,
            "Robot Inteligente 4WD | Validacion digital; prueba impresa pendiente",
        )
        pdf.showPage()
    pdf.save()
    return target


if __name__ == "__main__":
    optional = ROOT / ".tools" / "pdf_deps"
    if optional.exists():
        sys.path.append(str(optional))
    print(generate())
