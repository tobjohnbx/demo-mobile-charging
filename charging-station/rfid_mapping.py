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
        contract_id="2117046",
        debtor_ident="06cc07ed-8aa4-4111-ab75-a39ff18aba2c",
        contract_ident="3710a184-b0bc-49cf-998b-7c15213b99ea"
    ),
    "868383524177": CustomerInfo(
        contract_id="2118389",
        debtor_ident="c4b14198-4fc1-4ef2-bc82-1f568f8bbd0a",
        contract_ident="4e1ae42a-6df9-4f39-9afe-185672483251"
    ),
    "572221031092": CustomerInfo(
        contract_id="2118579",
        debtor_ident="6975df23-fdd2-4388-93a9-9f59cd126b0b",
        contract_ident="6975df23-fdd2-4388-93a9-9f59cd126b0b"
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
