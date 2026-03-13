"""
Serviço de geração de QR Code para visitantes.

O QR Code contém apenas o UUID do visitante — nenhum dado pessoal.
Isso garante que, mesmo que o QR seja fotografado por alguém,
não há como extrair nome, CPF ou apartamento a partir dele.
"""
import io

import qrcode
import qrcode.constants
from django.core.files.uploadedfile import InMemoryUploadedFile


def gerar_qr_code(visitante) -> InMemoryUploadedFile:
    """
    Gera a imagem PNG do QR Code para um visitante aprovado.

    Args:
        visitante: instância do model Visitante (já salvo no banco, com qr_code_id)

    Returns:
        InMemoryUploadedFile pronto para ser salvo em visitante.qr_code_imagem
    """
    # O payload é só o UUID — opaco e sem dados pessoais
    payload = str(visitante.qr_code_id)

    qr = qrcode.QRCode(
        version=1,
        # ERROR_CORRECT_H = 30% de redundância — o QR ainda funciona com partes danificadas
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    imagem = qr.make_image(fill_color="black", back_color="white")

    # Salva em memória (sem criar arquivo temporário em disco)
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)

    nome_arquivo = f"qr_{visitante.qr_code_id}.png"

    return InMemoryUploadedFile(
        file=buffer,
        field_name="qr_code_imagem",
        name=nome_arquivo,
        content_type="image/png",
        size=buffer.getbuffer().nbytes,
        charset=None,
    )
