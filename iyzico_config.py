import os
from dotenv import load_dotenv
import iyzipay

# .env dosyasındaki gizli verileri yükle
load_dotenv()

# Iyzico Ayarları (Şifreler artık güvende ve .env dosyasından okunuyor)
options = {
    'api_key': os.getenv('IYZICO_API_KEY'),
    'secret_key': os.getenv('IYZICO_SECRET_KEY'),
    'base_url': os.getenv('IYZICO_BASE_URL')
}

# Iyzico'nun form özelliklerini ayarladığımız obje
def get_iyzipay_options():
    return options