"""Small local PDF fixture with clearly distinguishable pages."""
from io import BytesIO
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def sample_pdf():
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    colors = ['0.09 0.22 0.18', '0.20 0.15 0.10', '0.12 0.18 0.30']
    for index, color in enumerate(colors):
        page = writer.add_blank_page(width=420, height=594)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        content = DecodedStreamObject()
        content.set_data((f'{color} rg 0 0 420 594 re f\n1 1 1 rg\n'
                          f'BT /F1 26 Tf 36 490 Td (ESTUDO DE XADREZ) Tj 0 -48 Td '
                          f'/F1 16 Tf (Pagina {index + 1}) Tj 0 -60 Td '
                          f'(Controle o centro. Desenvolva suas pecas.) Tj ET').encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(content)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
