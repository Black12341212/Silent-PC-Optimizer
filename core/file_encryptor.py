import os
import hashlib
import base64
from core.logger import logger


def _derive_key(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return key, salt


def encrypt_file(file_path, password, output_path=None):
    if not output_path:
        output_path = file_path + ".encrypted"
    try:
        key, salt = _derive_key(password)
        with open(file_path, "rb") as f:
            data = f.read()
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding as sym_padding
        iv = os.urandom(16)
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        with open(output_path, "wb") as f:
            f.write(salt + iv + encrypted)
        logger.info(f"Файл зашифрован: {file_path} -> {output_path}")
        return True, output_path
    except ImportError:
        logger.error("cryptography не установлена: pip install cryptography")
        return False, "cryptography library not installed"
    except Exception as e:
        logger.error(f"Ошибка шифрования: {e}")
        return False, str(e)


def decrypt_file(file_path, password, output_path=None):
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        salt = raw[:16]
        iv = raw[16:32]
        encrypted_data = raw[32:]
        key, _ = _derive_key(password, salt)
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding as sym_padding
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        if not output_path:
            if file_path.endswith(".encrypted"):
                output_path = file_path[:-10]
            else:
                output_path = file_path + ".decrypted"
        with open(output_path, "wb") as f:
            f.write(data)
        logger.info(f"Файл расшифрован: {file_path} -> {output_path}")
        return True, output_path
    except ImportError:
        return False, "cryptography library not installed"
    except Exception as e:
        logger.error(f"Ошибка дешифрования: {e}")
        return False, str(e)
