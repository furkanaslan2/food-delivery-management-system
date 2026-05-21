import iyzipay

# Iyzico Test (Sandbox) Ortamı Ayarları
options = {
    'api_key': 'sandbox-gTdVJFYxWfHqVbCE0AlG8IGHVkW1APFN',
    'secret_key': 'sandbox-GZzdesydtXCDQg2LdXk5EQX6Dp0pNeDK',
    'base_url': 'sandbox-api.iyzipay.com'
}

# Iyzico'nun form özelliklerini ayarladığımız obje
def get_iyzipay_options():
    return options