# 4. Level 3: signing

Level 3 ("Verified") wraps a Level 2 passport in a **W3C Verifiable
Credential** and signs it. Anyone can then check, with standard software and
no account on your system, that:

- the passport was issued by you (signature matches your published key);
- it has not been altered since (any change breaks the signature);
- it has not been withdrawn (a revocation list says so).

## Honest status first

| What | Status (November 2026) |
|---|---|
| Specification of Level 3 | Normative (spec §6, §8) |
| `tools/validate.py` recognising signed passports and reporting Level 3 | Done |
| `tools/validate.py` checking the signature | **Not done.** It prints a warning saying so. |
| Reference issuance (signing service with managed keys) | **Not yet implemented.** KMS-held per-organisation keys are in the WP2 backlog. |
| Signature verification in `POST /verify` | Part of the WP2 reference implementation (D2.2) |
| Hosted signing service for SMEs without their own key management | Open question (spec open issue 5) |

So today you can **produce** Level 3 passports with your own tooling or a
commercial platform, and **check structure** with `validate.py`. Use a
standard VC library or the reference verifier, when released, for signature
checks. See `IMPLEMENTATION_STATUS.md` for the current position.

## The two ways to sign

Both use the same key type: **ECDSA on curve P-256**. A Level 3 verifier must
accept both; issuers should prefer the first.

| | VC-JOSE (preferred) | Data Integrity (permitted alternative) |
|---|---|---|
| Standard | W3C *Securing Verifiable Credentials using JOSE and COSE* | W3C Data Integrity, cryptosuite `ecdsa-jcs-2019` |
| Algorithm | `ES256` (ECDSA P-256 with SHA-256) | ECDSA P-256 over the JCS (RFC 8785) canonical JSON |
| What the file looks like | One line of text: `header.payload.signature` (compact JWS), not JSON | The credential JSON with a `proof` block added |
| Header / proof | `{"alg":"ES256","typ":"vc+jwt","kid":"<key URL>"}` | `"proof": {"type":"DataIntegrityProof","cryptosuite":"ecdsa-jcs-2019","verificationMethod":"<key URL>", ...}` |
| Media type in the API | `application/vc+jwt` | `application/ld+json` |
| Why choose it | Matches the EU DPP direction (CIRPASS-2 and UNTP converged on JOSE); every JWT library can check it | The credential stays readable JSON |

`examples/example_passport.jsonld` shows the Data Integrity form (its
signature value is illustrative, not real).

## What goes in the credential

The passport you already have becomes `credentialSubject`. Around it:

```json
{
  "@context": [
    "https://www.w3.org/ns/credentials/v2",
    "https://ref.gs1.org/standards/epcis/epcis-context.jsonld",
    "https://schema.materialspassport.org.uk/v0.2/context.jsonld",
    "https://schema.materialspassport.org.uk/v0.1/plastics-context.jsonld"
  ],
  "id": "https://id.gs1.org/01/05060987654338/10/PP-2026-0150",
  "type": ["VerifiableCredential", "MaterialPassportCredential"],
  "issuer": { "id": "https://passports.example-sme.co.uk/issuer", "name": "Example SME Reprocessing Ltd" },
  "validFrom": "2026-10-23T00:00:00Z",
  "credentialStatus": {
    "id": "https://passports.example-sme.co.uk/status/1#4021",
    "type": "BitstringStatusListEntry",
    "statusPurpose": "revocation",
    "statusListIndex": "4021",
    "statusListCredential": "https://passports.example-sme.co.uk/status/1"
  },
  "credentialSubject": { "type": "ukmp:MaterialPassport", "...": "your Level 2 passport" }
}
```

- `issuer.id` is an HTTPS address for your organisation (a `did:web`
  identifier also works).
- `credentialStatus` is your entry in a **Bitstring Status List**: a published,
  signed list of on/off bits. Flipping your bit revokes the passport (recall,
  withdrawal) without needing to contact everyone who has a copy. The API
  serves the list at `GET /status/{listId}` and flips the bit with
  `POST /passports/{id}/status` (chapter 5).
- Set `credentialSubject.conformanceLevel` to `3`.

## Publishing your keys at /.well-known

Verifiers find your public key from the `kid` (JOSE) or `verificationMethod`
(Data Integrity) URL. The exchange API publishes keys at:

```
GET https://<your-issuer-host>/.well-known/ukmp/keys
```

It returns a standard JSON Web Key Set (JWKS):

```json
{
  "keys": [
    {
      "kty": "EC",
      "crv": "P-256",
      "alg": "ES256",
      "use": "sig",
      "kid": "https://passports.example-sme.co.uk/.well-known/ukmp/keys#2026-1",
      "x": "sRWpdydO25ad2H2yZZopbt-fv1B9ref2c-7hd5S6rNM",
      "y": "dK5iOaQ0-2QiP_i9GCA7hQ8iyilDat0U5wnxmJDwMAU"
    }
  ]
}
```

Key management rules:

1. **Never delete an old public key.** Passports signed years ago must still
   verify. Keep current and historical keys in the set; give each a new
   `kid` when you rotate. The API marks each key with `ukmp:status`
   (`current` or `retired`) and `ukmp:validFrom` / `ukmp:validUntil`.
2. **Keep the private key out of files and spreadsheets.** Production keys
   belong in a hardware security module or cloud key management service
   (KMS), with signing done by a service that never exports the key.
3. If a private key may have leaked, revoke the passports signed with it
   (status list) and re-issue them under a new key.
4. Serve `/.well-known/ukmp/keys` over HTTPS from the same domain as
   `issuer.id`.

## Try it: sign a passport yourself (experiment only)

Because reference issuance is not available yet, here is a short experiment
so IT suppliers can see the mechanics. It uses the Python `cryptography`
package and a key in a file, which is fine for learning and **not** for
production.

```bash
pip install cryptography
```

```
$ openssl ecparam -name prime256v1 -genkey -noout -out issuer-key.pem
$ python docs/user-guide/examples/sign_demo.py sign issuer-key.pem docs/user-guide/examples/level2_pp_pellet.jsonld PP-2026-0150.jwt
wrote PP-2026-0150.jwt (header {'alg': 'ES256', 'typ': 'vc+jwt', 'kid': 'https://passports.example-sme.co.uk/.well-known/ukmp/keys#2026-1'})
$ python docs/user-guide/examples/sign_demo.py verify issuer-key.pem PP-2026-0150.jwt
signature OK: {'alg': 'ES256', 'typ': 'vc+jwt', 'kid': 'https://passports.example-sme.co.uk/.well-known/ukmp/keys#2026-1'}
$ python tools/validate.py PP-2026-0150.jwt
[PASS]  PP-2026-0150.jwt (JOSE-enveloped (JWS))
        detected conformance level: 3 (Verified)
        identity level: batch (declared)
        ! jose: JWS signature present but NOT cryptographically verified by this tool (Level 3 signature verification is a WP2 reference-implementation capability)

1/1 file(s) valid
$ python docs/user-guide/examples/sign_demo.py jwk issuer-key.pem
```

The last command prints the public key as a JWKS, exactly the document you
would publish at `/.well-known/ukmp/keys` (the example earlier in this chapter
came from one run of it; your key will differ).

Points to notice:

- The `.jwt` file is not JSON. `validate.py` detects that, decodes the middle
  part, and checks the passport inside.
- The validator says Level 3 because the passport is enveloped and secured
  and the inner claim is Level 2, but it warns that it did not check the
  signature. `sign_demo.py verify` did check it, using the key.
- An ECDSA JWS signature is the raw 64-byte `r||s` value, not the DER
  encoding most crypto libraries produce. `sign_demo.py` converts between
  them; forgetting this is the most common home-made JWS bug.
- Change one character in the payload and `verify` fails.

## Data Integrity (ecdsa-jcs-2019) in outline

If you use this form instead:

1. Build the credential JSON (without `proof`).
2. Build the proof options (`type`, `cryptosuite`, `created`,
   `verificationMethod`, `proofPurpose: assertionMethod`).
3. Canonicalise both with JCS (RFC 8785), hash each with SHA-256, and sign
   the concatenated hashes with the same P-256 key.
4. Encode the signature as multibase base58-btc (`z...`) in `proofValue`.

Use a maintained Data Integrity library rather than writing this yourself;
canonicalisation details are easy to get subtly wrong.

## Checklist: Level 2 to Level 3

- [ ] Passport validates at Level 2 first.
- [ ] Issuer HTTPS identity decided (`issuer.id`), keys in KMS/HSM.
- [ ] `/.well-known/ukmp/keys` published with every key ever used.
- [ ] Status list published; each passport has a `credentialStatus` entry.
- [ ] Signed with ES256 as `vc+jwt` (preferred) or `ecdsa-jcs-2019`.
- [ ] Signature checked with an independent verifier, not just `validate.py`.
