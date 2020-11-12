# coding=utf-8
import base64
import logging

from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

logger = logging.getLogger(__name__)


def gen_key():
    random_generator = Random.new().read
    rsa = RSA.generate(1024, random_generator)
    private_key = rsa.exportKey()
    public_key = rsa.publickey().exportKey()
    return private_key, public_key


def encrypt(public_key, data):
    rsakey = RSA.importKey(public_key)
    cipher = PKCS1_v1_5.new(rsakey)
    cipher_text = base64.b64encode(cipher.encrypt(data.encode('utf-8')))
    return cipher_text


def decrypt(private_key, data):
    random_generator = Random.new().read
    cipher = PKCS1_v1_5.new(private_key)
    text = cipher.decrypt(base64.b64decode(data), random_generator)
    return text
