import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from src.config import get_config


PII_TYPE_MAPPING = {
    "PERSON": "person_name",
    "EMAIL_ADDRESS": "email",
    "PHONE_NUMBER": "phone",
    "CREDIT_CARD": "credit_card",
    "SSN": "ssn",
    "DATE_OF_BIRTH": "date_of_birth",
    "US_SSN": "ssn",
    "US_DRIVER_LICENSE": "driver_license",
    "US_PASSPORT": "passport",
    "IP_ADDRESS": "ip_address",
    "IBAN_CODE": "iban",
    "CRYPTO": "crypto_address",
    "ORGANIZATION": "organization",
    "LOCATION": "location",
}


@dataclass
class PIIResult:
    text: str
    pii_entities: List[Dict[str, Any]]
    pii_count: int
    original_text_length: int
    masked_text_length: int


class PIIMasker:
    def __init__(self, config=None):
        self.config = config or get_config()
        self._analyzer = None
        self._anonymizer = None
    
    @property
    def analyzer(self) -> AnalyzerEngine:
        if self._analyzer is None:
            self._analyzer = AnalyzerEngine()
        return self._analyzer
    
    @property
    def anonymizer(self) -> AnonymizerEngine:
        if self._anonymizer is None:
            self._anonymizer = AnonymizerEngine()
        return self._anonymizer
    
    def analyze(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        results = self.analyzer.analyze(text, language=language)
        
        pii_entities = []
        for result in results:
            entity_type = PII_TYPE_MAPPING.get(result.entity_type, result.entity_type)
            pii_entities.append({
                "entity_type": entity_type,
                "text": result.text,
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "label": result.entity_type
            })
        
        return pii_entities
    
    def mask(self, text: str, language: str = "en", 
             custom_replacements: Optional[Dict[str, str]] = None) -> PIIResult:
        analyzed_results = self.analyzer.analyze(text, language=language)
        
        pii_entities = []
        for result in analyzed_results:
            entity_type = PII_TYPE_MAPPING.get(result.entity_type, result.entity_type)
            pii_entities.append({
                "entity_type": entity_type,
                "text": result.text,
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "label": result.entity_type
            })
        
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzed_results,
            operators={
                "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})
            }
        )
        
        masked_text = anonymized_result.text
        
        return PIIResult(
            text=masked_text,
            pii_entities=pii_entities,
            pii_count=len(pii_entities),
            original_text_length=len(text),
            masked_text_length=len(masked_text)
        )
    
    def mask_batch(self, texts: List[str], language: str = "en") -> List[PIIResult]:
        results = []
        for text in texts:
            result = self.mask(text, language)
            results.append(result)
        return results
    
    def detect_pii(self, text: str, language: str = "en") -> Dict[str, Any]:
        pii_entities = self.analyze(text, language)
        
        return {
            "has_pii": len(pii_entities) > 0,
            "pii_count": len(pii_entities),
            "pii_entities": pii_entities,
            "pii_types": list(set(e["entity_type"] for e in pii_entities))
        }


def load_texts(path: str = "data/processed/chunks.jsonl") -> List[str]:
    texts = []
    file_path = Path(path)
    
    if not file_path.exists():
        file_path = Path(__file__).parent.parent.parent / path
    
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                texts.append(data.get("text", ""))
    
    return texts


def main():
    config = get_config()
    masker = PIIMasker(config)
    
    test_texts = [
        "Patient John Smith (SSN: 123-45-6789) visited on 2024-01-15. Contact: john.smith@email.com or 555-123-4567",
        "The policy POL-2024-001 covers hospitalization up to $100,000.",
        "Claim can be filed at claims@insurance.com or call 1-800-INSURE-01"
    ]
    
    print("PII Detection Results:")
    print("=" * 60)
    
    for text in test_texts:
        result = masker.mask(text)
        print(f"\nOriginal: {text[:80]}...")
        print(f"Masked: {result.text[:80]}...")
        print(f"PII Count: {result.pii_count}")
        print(f"Entities: {result.pii_entities}")


if __name__ == "__main__":
    import json
    from pathlib import Path
    main()
