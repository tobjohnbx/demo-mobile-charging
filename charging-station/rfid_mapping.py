from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class CustomerInfo:
    contract_id: str
    debtor_ident: str
    contract_ident: str


# Static mapping of RFID tag numbers to customer information
RFID_TAG_MAPPING: Dict[str, CustomerInfo] = {
    "316922528399": CustomerInfo(
        contract_id="2118901",
        debtor_ident="06cc07ed-8aa4-4111-ab75-a39ff18aba2c",
        contract_ident="cc563506-a370-498b-812d-0a4beb722956"
    ),
    "868383524177": CustomerInfo(
        contract_id="2118899",
        debtor_ident="c4b14198-4fc1-4ef2-bc82-1f568f8bbd0a",
        contract_ident="0bc2dd8c-8ccc-4597-950b-abedd7aa508a"
    ),
    "572221031092": CustomerInfo(
        contract_id="2118900",
        debtor_ident="ae802008-bcbf-466d-be70-1fe612066c2b",
        contract_ident="be7d5ec4-48b3-4cbc-85e9-f0e7ed1a9d07"
    )
}


def get_customer_info(rfid_tag: str) -> Optional[CustomerInfo]:
    """
    Get customer information for a given RFID tag.
    
    Args:
        rfid_tag: The RFID tag identifier
        
    Returns:
        CustomerInfo if the tag exists in the mapping, None otherwise
    """
    return RFID_TAG_MAPPING.get(rfid_tag)
