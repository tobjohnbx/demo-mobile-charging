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
        contract_id="2118902",
        debtor_ident="06cc07ed-8aa4-4111-ab75-a39ff18aba2c",
        contract_ident="54156c4a-00a6-462d-ba2c-f82d016fc376"
    ),
    "868383524177": CustomerInfo(
        contract_id="2118903",
        debtor_ident="c4b14198-4fc1-4ef2-bc82-1f568f8bbd0a",
        contract_ident="7114be43-508c-433c-9dde-7a8b346a508e"
    ),
    "572221031092": CustomerInfo(
        contract_id="2118904",
        debtor_ident="ae802008-bcbf-466d-be70-1fe612066c2b",
        contract_ident="a007f215-f0e9-4c5e-8fcf-61c663197738"
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
