@dataclass(frozen=True)
class NitroboxConfig:
    api_url: str
    billing_url: str
    oauth_url: str
    client_credentials_b64: str
    contract_id: int
    product_ident: str
    debtor_ident: str

    @staticmethod
    def from_env() -> "NitroboxConfig":
        try:
            return NitroboxConfig(
                api_url=os.environ.get(
                    "NITROBOX_API_URL",
                    "https://api.nbx-stage-westeurope.nitrobox.io/v2/usages",
                ),
                billing_url=os.environ.get(
                    "NITROBOX_BILLING_URL",
                    "https://api.nbx-stage-westeurope.nitrobox.io/v2/billingrun",
                ),
                oauth_url=os.environ.get(
                    "NITROBOX_OAUTH_URL",
                    "https://api.nbx-stage-westeurope.nitrobox.io/demo-mobile-charging/oauth2/token",
                ),
                client_credentials_b64=os.environ["NITROBOX_CLIENT_CREDENTIALS"],
                contract_id=int(os.environ.get("NITROBOX_CONTRACT_ID", 2117046)),
                product_ident=os.environ.get(
                    "NITROBOX_PRODUCT_IDENT",
                    "9788b7d9-ab3e-4d7e-a483-258d12bc5078",
                ),
                debtor_ident=os.environ.get(
                    "NITROBOX_DEBTOR_IDENT",
                    "06cc07ed-8aa4-4111-ab75-a39ff18aba2c",
                ),
            )
        except KeyError as e:
            missing = str(e).strip("'")
            raise RuntimeError(
                f"Missing required environment variable: {missing}"
            ) from None