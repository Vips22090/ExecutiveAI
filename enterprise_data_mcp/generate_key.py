"""
Run this once to generate a private/public key pair for Snowflake key-pair auth.
No OpenSSL needed -- just Python and the `cryptography` package
(pip install cryptography).

After running, you'll have two files:
    snowflake_key.p8   <- PRIVATE key. Never share this. Never commit to git.
    snowflake_key.pub  <- PUBLIC key. Safe to share -- this goes into Snowflake.
"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate a new 2048-bit RSA key pair
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Save the PRIVATE key (keep this file secret, add it to .gitignore)
with open("snowflake_key.p8", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))

# Save the PUBLIC key (this one is safe to share -- goes into Snowflake)
public_key = private_key.public_key()
with open("snowflake_key.pub", "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))

print("Done! Created:")
print("  snowflake_key.p8   (PRIVATE - keep secret, add to .gitignore)")
print("  snowflake_key.pub  (PUBLIC - safe to share with Snowflake)")
print()
print("Open snowflake_key.pub in a text editor next -- you'll copy its")
print("contents (between the BEGIN/END lines) into Snowflake in the next step.")
