import unittest

import server


class SignedProofTests(unittest.TestCase):
    def test_sign_and_verify(self):
        proof = server.sign_token({
            "iss": "test",
            "aud": "partner:test",
            "sub": "pairwise_abc",
            "iat": server.now(),
            "exp": server.now() + 60,
            "claims": {"real_human": True},
        })
        valid, payload, message = server.verify_token(proof)
        self.assertTrue(valid, message)
        self.assertEqual(payload["sub"], "pairwise_abc")

    def test_expired_proof(self):
        proof = server.sign_token({
            "iss": "test",
            "aud": "partner:test",
            "sub": "pairwise_abc",
            "iat": server.now() - 120,
            "exp": server.now() - 60,
            "claims": {"real_human": True},
        })
        valid, payload, message = server.verify_token(proof)
        self.assertFalse(valid)
        self.assertEqual(message, "Token expired")


if __name__ == "__main__":
    unittest.main()
