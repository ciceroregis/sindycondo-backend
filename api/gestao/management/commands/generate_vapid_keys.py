from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Gera par de chaves VAPID para Web Push notifications'

    def handle(self, *args, **options):
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
            import base64

            key = ec.generate_private_key(ec.SECP256R1())
            pub = key.public_key()

            pub_bytes = pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
            pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b'=').decode()
            priv_b64 = base64.urlsafe_b64encode(
                key.private_numbers().private_value.to_bytes(32, 'big')
            ).rstrip(b'=').decode()

            self.stdout.write(self.style.SUCCESS('Adicione ao seu .env:'))
            self.stdout.write(f'VAPID_PUBLIC_KEY={pub_b64}')
            self.stdout.write(f'VAPID_PRIVATE_KEY={priv_b64}')
            self.stdout.write(f'VAPID_ADMIN_EMAIL=admin@sindycondo.com.br')
        except ImportError:
            self.stderr.write('cryptography não instalado. Execute: pip install cryptography')
