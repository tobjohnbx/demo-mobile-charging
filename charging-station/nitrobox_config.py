import os
from dataclasses import dataclass


@dataclass(frozen=True)
class NitroboxConfig:
    api_url: str
    billing_url: str
    oauth_url: str
    client_credentials_b64: str
    product_ident: str
    option_ident: str
    contract_ident: str

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
                product_ident=os.environ.get(
                    "NITROBOX_PRODUCT_IDENT",
                    "9788b7d9-ab3e-4d7e-a483-258d12bc5078",
                ),
                option_ident=os.environ.get(
                    "NITROBOX_OPTION_IDENT",
                    "default-charging-option",  # Replace with actual value
                ),
                contract_ident=os.environ.get(
                    "NITROBOX_CONTRACT_IDENT",
                    "3710a184-b0bc-49cf-998b-7c15213b99ea",  # From your curl example
                ),
            )
        except KeyError as e:
            missing = str(e).strip("'")
            raise RuntimeError(
                f"Missing required environment variable: {missing}"
            ) from None
