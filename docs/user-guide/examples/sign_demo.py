"""UK Materials Passport user guide, chapter 4. Requires: pip install cryptography

EXPERIMENT ONLY: wrap a bare UKMP passport in a W3C VC and secure it as
a VC-JOSE compact JWS (ES256). Not the reference issuance service; keys in
files are not acceptable key custody for production.

    python docs/user-guide/examples/sign_demo.py sign   <issuer-key.pem> <passport.jsonld> <out.jwt>
    python docs/user-guide/examples/sign_demo.py verify <issuer-key.pem> <in.jwt>
    python docs/user-guide/examples/sign_demo.py jwk    <issuer-key.pem>
"""
import base64, json, sys
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature, encode_dss_signature)

ISSUER = "https://passports.example-sme.co.uk/issuer"
KID = "https://passports.example-sme.co.uk/.well-known/ukmp/keys#2026-1"

def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def unb64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))

def load_key(path):
    return serialization.load_pem_private_key(open(path, "rb").read(), password=None)

def sign(key_path, passport_path, out_path):
    subject = json.load(open(passport_path))
    contexts = subject.pop("@context", [])
    subject["conformanceLevel"] = 3
    vc = {
        "@context": ["https://www.w3.org/ns/credentials/v2"] + contexts,
        "id": subject["passportId"],
        "type": ["VerifiableCredential", "MaterialPassportCredential"],
        "issuer": {"id": ISSUER, "name": subject["issuerParty"]["name"]},
        "validFrom": subject["issueDate"] + "T00:00:00Z",
        "credentialStatus": {
            "id": "https://passports.example-sme.co.uk/status/1#4021",
            "type": "BitstringStatusListEntry", "statusPurpose": "revocation",
            "statusListIndex": "4021",
            "statusListCredential": "https://passports.example-sme.co.uk/status/1"},
        "credentialSubject": subject,
    }
    header = {"alg": "ES256", "typ": "vc+jwt", "kid": KID}
    signing_input = f"{b64u(json.dumps(header).encode())}.{b64u(json.dumps(vc).encode())}"
    der = load_key(key_path).sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)            # JWS wants raw r||s, 32 bytes each
    sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    open(out_path, "w").write(f"{signing_input}.{b64u(sig)}")
    print(f"wrote {out_path} (header {header})")

def verify(key_path, jwt_path):
    h, p, s = open(jwt_path).read().strip().split(".")
    raw = unb64u(s)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    load_key(key_path).public_key().verify(der, f"{h}.{p}".encode(), ec.ECDSA(hashes.SHA256()))
    print("signature OK:", json.loads(unb64u(h)))

def jwk(key_path):
    nums = load_key(key_path).public_key().public_numbers()
    print(json.dumps({"keys": [{"kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig",
        "kid": KID, "x": b64u(nums.x.to_bytes(32, "big")), "y": b64u(nums.y.to_bytes(32, "big"))}]},
        indent=2))

if __name__ == "__main__":
    {"sign": sign, "verify": verify, "jwk": jwk}[sys.argv[1]](*sys.argv[2:])
