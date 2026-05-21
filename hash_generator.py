from werkzeug.security import generate_password_hash

print("--- Flask Şifre Üretici ---")
password = input("Şifrelenecek parolayı girin (Örn: 123456): ")

# pbkdf2:sha256 algoritmasını kullanmaya zorluyoruz
hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

print("\nKopyalayıp MySQL Workbench'te 'password' sütununa yapıştıracağınız kod:")
print("-" * 50)
print(hashed_password)
print("-" * 50)