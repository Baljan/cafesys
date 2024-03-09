from base64 import b64decode
from uuid import UUID

from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import jwt
from social_core.backends.oauth import BaseOAuth2
from social_core.exceptions import AuthTokenError

LIU_X509_CERT = 'MIIDLTCCAhWgAwIBAgIQFPektIXgbZRBYUGmou4GaDANBgkqhkiG9w0BAQsFADAbMRkwFwYDVQQDDBBmc3NpZ25pbmcubGl1LnNlMB4XDTE3MTIxNTA3NDM0N1oXDTI3MTIxNTA3NTM0N1owGzEZMBcGA1UEAwwQZnNzaWduaW5nLmxpdS5zZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALbCDIqrM4xMhU9tKSgJaDyK+JGWw/lHsasvDfHVk33ocobSTkJypNESx9oS6ToOmD+W25/6rUlSJBsYb6TdasNP7zcxqPdTd1pFO15U4rchRVGn1+GK3FZPbhqTY0sdc6Wba0w9EiroxQ92AO6boQfgUded3CQuJx76xPtoQCGJaObIrhQGwm9O8hXdfUclP2+cUm4I3pN7LV5MM7R1rrJrmXAtcHx81lNwE/OA97k+E5stpDAMfmcL8Ccd2UDD3fbyZuPjnw566mJnilq/17eDm0ZinSfXN0b5E7Be3T1By2L8dYnyAsdWR9j27JnF/0QFQrypvvG+V7p3/PTegg8CAwEAAaNtMGswDgYDVR0PAQH/BAQDAgWgMB0GA1UdJQQWMBQGCCsGAQUFBwMCBggrBgEFBQcDATAbBgNVHREEFDASghBmc3NpZ25pbmcubGl1LnNlMB0GA1UdDgQWBBRRcAPfymvTMLgK5jMTzffTb6uTXzANBgkqhkiG9w0BAQsFAAOCAQEAJILiWPT6+wlSt70xEi/b2rXFgKc16HqFvHGzMUnU2goDAWje3R9hFQJe53btvOuhlCCVgHnjuQsyeSeK50vLG8N7PUL+TzqqVCpsk56BJeg3399mJ610S41x8b27hw6icz95mBWdTztScjyJYg6n/hQYf48auRXMVUTJ8ckUl72/NWrQvZ3XouyNV9S2A3DC1qtCF875TipSxbUOM2V77GwXH2sdanMfhsGQYoTsZ5qE0qnjuQWVDiRnOMnvRnvzDAlCKjRtAqGlOLMOIHLqu8bHcIBe4v+veexfA6vNpgY75s2JxiNUDN6BEHmvl4q0e9M30gZl5SjvG2o/9A8zsw=='  # noqa


# Don't use this directly. Will probably be broken out from this package.
class ADFSOAuth2(BaseOAuth2):
    name = 'adfs'

    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_PARAMETER_NAME = 'resource'

    DEFAULT_HOST = None
    DEFAULT_X509_CERT = None

    token_payload = None

    def get_host(self):
        return self.setting('HOST', default=self.DEFAULT_HOST)

    def get_x509_cert(self):
        return self.setting('X509_CERT', default=self.DEFAULT_X509_CERT)

    def authorization_url(self):
        return 'https://{0}/adfs/oauth2/authorize'.format(self.get_host())

    def access_token_url(self):
        return 'https://{0}/adfs/oauth2/token'.format(self.get_host())

    def issuer_url(self):
        return 'http://{0}/adfs/services/trust'.format(self.get_host())

    def get_token_key(self):
        raw_cert = self.get_x509_cert()
        # b64decode freaks out over unpadded base64, so we must pad it if
        # needed. See
        # http://stackoverflow.com/questions/2941995#comment12174484_2942039
        padded_raw_cert = raw_cert + '=' * (-len(raw_cert) % 4)
        cert = load_der_x509_certificate(b64decode(padded_raw_cert),
                                         default_backend())

        return cert.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def request_access_token(self, *args, **kwargs):
        response = super(ADFSOAuth2, self).request_access_token(*args, **kwargs)

        try:
            self.token_payload = jwt.decode(
                response.get('access_token'),
                audience=self.get_scope_argument()[self.SCOPE_PARAMETER_NAME],
                key=self.get_token_key(),
                leeway=self.setting('LEEWAY', 0),
                iss=self.issuer_url(),
                algorithms=[
                    "HS256",
                    "HS384",
                    "HS512",
                    "RS256",
                    "RS384",
                    "RS512",
                    "ES256",
                    "ES256K",
                    "ES384",
                    "ES521",
                    "ES512",
                    "PS256",
                    "PS384",
                    "PS512",
                    "EdDSA",
                ],
                options=dict(
                    verify_signature=True,
                    verify_exp=True,
                    verify_nbf=False,
                    verify_iat=self.setting('VERIFY_IAT', True),
                    verify_aud=True,
                    verify_iss=True,
                    require_exp=True,
                    require_iat=True,
                    require_nbf=False
                )
            )
        except jwt.InvalidTokenError as exc:
            raise AuthTokenError(self, exc)

        return response

    def get_user_id(self, details, response):
        return str(UUID(bytes_le=b64decode(self.token_payload.get('ppid'))))

    def get_user_details(self, response):
        return dict(
            # sub = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier
            username=self.token_payload.get('sub').split('@')[0],
            # email = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress
            email=self.token_payload.get('email'),
            # unique_name = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name
            fullname=self.token_payload.get('unique_name'),
            # given_name = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname
            first_name=self.token_payload.get('given_name'),
            # family_name = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname
            last_name=self.token_payload.get('family_name')
        )


class LiuBackend(ADFSOAuth2):
    name = 'liu'

    EXTRA_DATA = [
        ('nor_edu_person_lin', 'nor_edu_person_lin'),
    ]

    DEFAULT_HOST = 'fs.liu.se'
    DEFAULT_X509_CERT = LIU_X509_CERT

    def user_data(self, access_token, *args, **kwargs):
        return dict(
            nor_edu_person_lin=self.token_payload.get(
                'http://liu.se/claims/norEduPersonLIN')
        )
