import pytest

from src.pii.masker import PIIMasker
from src.config import get_config


class TestPIIMasking:
    @pytest.fixture
    def config(self):
        return get_config()
    
    @pytest.fixture
    def masker(self, config):
        return PIIMasker(config)
    
    def test_masker_initializes(self, masker):
        assert masker is not None
        assert masker.analyzer is not None
        assert masker.anonymizer is not None
    
    def test_detect_ssn(self, masker):
        text = "My SSN is 123-45-6789"
        result = masker.detect_pii(text)
        
        assert result["has_pii"] is True
        assert result["pii_count"] > 0
    
    def test_detect_email(self, masker):
        text = "Contact me at john.doe@example.com"
        result = masker.detect_pii(text)
        
        assert result["has_pii"] is True
        assert "email" in result["pii_types"]
    
    def test_detect_phone(self, masker):
        text = "Call me at 555-123-4567"
        result = masker.detect_pii(text)
        
        assert result["has_pii"] is True
        assert result["pii_count"] > 0
    
    def test_mask_ssn(self, masker):
        text = "My SSN is 123-45-6789"
        result = masker.mask(text)
        
        assert "[REDACTED]" in result.text
        assert "123-45-6789" not in result.text
        assert result.pii_count > 0
    
    def test_mask_email(self, masker):
        text = "Email: john.doe@example.com"
        result = masker.mask(text)
        
        assert "[REDACTED]" in result.text
    
    def test_mask_phone(self, masker):
        text = "Phone: 555-123-4567"
        result = masker.mask(text)
        
        assert "[REDACTED]" in result.text
    
    def test_no_pii_text(self, masker):
        text = "What is the coverage for hospitalization?"
        result = masker.detect_pii(text)
        
        assert result["has_pii"] is False
        assert result["pii_count"] == 0
    
    def test_batch_masking(self, masker):
        texts = [
            "SSN: 123-45-6789",
            "Email: test@example.com",
            "What is the deductible?"
        ]
        
        results = masker.mask_batch(texts)
        
        assert len(results) == 3
        assert results[0].pii_count > 0
        assert results[1].pii_count > 0
        assert results[2].pii_count == 0
    
    def test_insurance_policy_pii(self, masker):
        text = """
        Policy Holder: John Smith
        SSN: 987-65-4321
        Email: john.smith@insurance.com
        Phone: 555-999-8888
        
        The policy covers hospitalization up to $100,000.
        """
        
        result = masker.mask(text)
        
        assert result.pii_count > 0
        assert "[REDACTED]" in result.text
        
        assert "987-65-4321" not in result.text
        assert "john.smith@insurance.com" not in result.text
        assert "555-999-8888" not in result.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
