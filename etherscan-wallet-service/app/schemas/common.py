from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

ETH_ADDRESS_PATTERN = r"^0x[a-fA-F0-9]{40}$"
EthereumAddress = Annotated[str, StringConstraints(pattern=ETH_ADDRESS_PATTERN)]
SortOrder = Literal["asc", "desc"]


class HealthResponse(BaseModel):
    status: str = "ok"


class CommonTxQueryParams(BaseModel):
    chain_id: int = Field(default=1, gt=0)
    start_block: int = Field(default=0, ge=0)
    end_block: int = Field(default=999_999_999, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)
    sort: SortOrder = "desc"

    @model_validator(mode="after")
    def validate_block_range(self) -> Self:
        if self.end_block < self.start_block:
            raise ValueError("end_block must be greater than or equal to start_block")
        return self


class Erc20TxQueryParams(CommonTxQueryParams):
    contract_address: EthereumAddress | None = None
