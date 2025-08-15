from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class CustomerInfo:
    contract_id: int
    debtor_ident: str


# Static mapping of RFID tag numbers to customer information
RFID_TAG_MAPPING: Dict[str, CustomerInfo] = {
    "316922528399": CustomerInfo(
        contract_id=2117046,
        debtor_ident="06cc07ed-8aa4-4111-ab75-a39ff18aba2c"
    ),
    "868383524177": CustomerInfo(
        contract_id=2118389,
        debtor_ident="c4b14198-4fc1-4ef2-bc82-1f568f8bbd0a"
    ),
    "572221031092": CustomerInfo(
        contract_id=2118579,
        debtor_ident="ae802008-bcbf-466d-be70-1fe612066c2b"
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
