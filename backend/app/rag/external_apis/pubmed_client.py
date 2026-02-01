"""
PubMed API Client for fetching health research abstracts.

Uses NCBI E-utilities API to search and retrieve PubMed articles.
https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""

import httpx
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from xml.etree import ElementTree
import re

from app.config import settings


@dataclass
class PubMedArticle:
    """Represents a PubMed article."""
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    pub_date: str
    keywords: List[str]
    mesh_terms: List[str]
    doi: Optional[str] = None
    
    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = [
            f"Title: {self.title}",
            f"Journal: {self.journal} ({self.pub_date})",
            f"Authors: {', '.join(self.authors[:5])}{'...' if len(self.authors) > 5 else ''}",
            "",
            "Abstract:",
            self.abstract,
        ]
        
        if self.keywords:
            parts.append(f"\nKeywords: {', '.join(self.keywords)}")
        
        if self.mesh_terms:
            parts.append(f"MeSH Terms: {', '.join(self.mesh_terms[:10])}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pmid": self.pmid,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "journal": self.journal,
            "pub_date": self.pub_date,
            "keywords": self.keywords,
            "mesh_terms": self.mesh_terms,
            "doi": self.doi,
        }


class PubMedClient:
    """
    Async client for PubMed/NCBI E-utilities API.
    
    Features:
    - Search articles by query
    - Fetch abstracts by PMID
    - Rate limiting support
    - Error handling
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Health-relevant search queries for VitalIQ
    HEALTH_QUERIES = {
        "sleep": "(sleep quality[Title/Abstract]) AND (health outcomes[Title/Abstract])",
        "hrv": "(heart rate variability[Title/Abstract]) AND (health[Title/Abstract])",
        "exercise": "(exercise[Title/Abstract]) AND (health benefits[Title/Abstract])",
        "nutrition": "(nutrition[Title/Abstract]) AND (metabolic health[Title/Abstract])",
        "glucose": "(blood glucose[Title/Abstract]) AND (lifestyle[Title/Abstract])",
        "stress": "(stress[Title/Abstract]) AND (physiological markers[Title/Abstract])",
    }
    
    def __init__(self):
        self.email = settings.PUBMED_EMAIL
        self.api_key = settings.PUBMED_API_KEY
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _build_params(self, **kwargs) -> Dict[str, str]:
        """Build request parameters with credentials."""
        params = {"tool": "VitalIQ", "email": self.email, **kwargs}
        if self.api_key:
            params["api_key"] = self.api_key
        return params
    
    async def search_articles(
        self, 
        query: str, 
        max_results: int = 100,
        sort: str = "relevance"
    ) -> List[str]:
        """
        Search PubMed for articles matching query.
        
        Args:
            query: Search query string
            max_results: Maximum number of PMIDs to return
            sort: Sort order ('relevance' or 'pub_date')
            
        Returns:
            List of PMIDs
        """
        params = self._build_params(
            db="pubmed",
            term=query,
            retmax=str(max_results),
            sort=sort,
            retmode="json"
        )
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            result = data.get("esearchresult", {})
            pmids = result.get("idlist", [])
            
            return pmids
            
        except httpx.HTTPError as e:
            print(f"PubMed search error: {e}")
            return []
    
    async def fetch_abstracts(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch article details for given PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of PubMedArticle objects
        """
        if not pmids:
            return []
        
        # Fetch in batches of 100
        articles = []
        batch_size = 100
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            batch_articles = await self._fetch_batch(batch)
            articles.extend(batch_articles)
            
            # Rate limiting: NCBI allows 3 requests/second without API key
            if not self.api_key:
                await asyncio.sleep(0.35)
        
        return articles
    
    async def _fetch_batch(self, pmids: List[str]) -> List[PubMedArticle]:
        """Fetch a batch of articles."""
        params = self._build_params(
            db="pubmed",
            id=",".join(pmids),
            retmode="xml",
            rettype="abstract"
        )
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/efetch.fcgi",
                params=params
            )
            response.raise_for_status()
            
            return self._parse_xml_response(response.text)
            
        except httpx.HTTPError as e:
            print(f"PubMed fetch error: {e}")
            return []
    
    def _parse_xml_response(self, xml_text: str) -> List[PubMedArticle]:
        """Parse XML response from efetch."""
        articles = []
        
        try:
            root = ElementTree.fromstring(xml_text)
            
            for article_elem in root.findall(".//PubmedArticle"):
                article = self._parse_article(article_elem)
                if article and article.abstract:
                    articles.append(article)
                    
        except ElementTree.ParseError as e:
            print(f"XML parse error: {e}")
        
        return articles
    
    def _parse_article(self, elem: ElementTree.Element) -> Optional[PubMedArticle]:
        """Parse a single article element."""
        try:
            # Get PMID
            pmid_elem = elem.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            # Get title
            title_elem = elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else ""
            
            # Get abstract
            abstract_parts = []
            for abstract_text in elem.findall(".//AbstractText"):
                label = abstract_text.get("Label", "")
                text = abstract_text.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)
            
            # Get authors
            authors = []
            for author in elem.findall(".//Author"):
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                if last_name is not None and fore_name is not None:
                    authors.append(f"{fore_name.text} {last_name.text}")
            
            # Get journal
            journal_elem = elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Get publication date
            pub_date = self._extract_pub_date(elem)
            
            # Get keywords
            keywords = [
                kw.text for kw in elem.findall(".//Keyword")
                if kw.text
            ]
            
            # Get MeSH terms
            mesh_terms = [
                mesh.text for mesh in elem.findall(".//MeshHeading/DescriptorName")
                if mesh.text
            ]
            
            # Get DOI
            doi = None
            for article_id in elem.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
            return PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                pub_date=pub_date,
                keywords=keywords,
                mesh_terms=mesh_terms,
                doi=doi
            )
            
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None
    
    def _extract_pub_date(self, elem: ElementTree.Element) -> str:
        """Extract publication date from article element."""
        # Try PubDate first
        pub_date = elem.find(".//PubDate")
        if pub_date is not None:
            year = pub_date.find("Year")
            month = pub_date.find("Month")
            day = pub_date.find("Day")
            
            parts = []
            if year is not None:
                parts.append(year.text)
            if month is not None:
                parts.append(month.text)
            if day is not None:
                parts.append(day.text)
            
            if parts:
                return " ".join(parts)
        
        # Try MedlineDate
        medline_date = elem.find(".//MedlineDate")
        if medline_date is not None and medline_date.text:
            return medline_date.text
        
        return "Unknown"
    
    async def search_and_fetch(
        self, 
        query: str, 
        max_results: int = 50
    ) -> List[PubMedArticle]:
        """
        Convenience method to search and fetch articles in one call.
        
        Args:
            query: Search query
            max_results: Maximum articles to return
            
        Returns:
            List of PubMedArticle objects with abstracts
        """
        pmids = await self.search_articles(query, max_results)
        if not pmids:
            return []
        
        return await self.fetch_abstracts(pmids)
    
    async def fetch_health_articles(
        self, 
        topics: Optional[List[str]] = None,
        max_per_topic: int = 20
    ) -> Dict[str, List[PubMedArticle]]:
        """
        Fetch articles for predefined health topics.
        
        Args:
            topics: List of topic keys (sleep, hrv, etc.) or None for all
            max_per_topic: Max articles per topic
            
        Returns:
            Dict mapping topic to list of articles
        """
        topics = topics or list(self.HEALTH_QUERIES.keys())
        results = {}
        
        for topic in topics:
            query = self.HEALTH_QUERIES.get(topic)
            if not query:
                continue
            
            articles = await self.search_and_fetch(query, max_per_topic)
            results[topic] = articles
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        return results
