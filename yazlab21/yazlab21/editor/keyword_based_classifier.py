from .keyword_extractor import clean_keyword

def classify_by_keywords(keywords):
    """
    Anahtar kelime listesine göre makaleyi sınıflandır.
    Mevcut anahtar kelimeleri kullanarak en uyumlu kategoriyi belirler.
    """
    if not keywords or not isinstance(keywords, list):
        return None, []
    
    keywords = [clean_keyword(kw) for kw in keywords]
    
    categories = [
        {
            "id": 1,
            "name": "1-Artificial Intelligence and Machine Learning",
            "keywords": [
                # Core AI/ML concepts
                "deep learning", "neural network", "machine learning", "artificial intelligence", "ai", 
                "supervised learning", "unsupervised learning", "reinforcement learning", "transfer learning",
                "feature extraction", "feature engineering", "model training", "model evaluation",
                "hyperparameter tuning", "overfitting", "underfitting", "bias", "variance",
                
                # Natural Language Processing
                "natural language processing", "nlp", "text analysis", "sentiment analysis", "language model",
                "text classification", "named entity recognition", "ner", "part-of-speech tagging", "pos tagging",
                "tokenization", "lemmatization", "stemming", "word embedding", "word2vec", "glove",
                "text generation", "text summarization", "machine translation", "speech recognition",
                "chatbot", "dialogue system", "question answering", "information extraction",
                
                # Computer Vision
                "computer vision", "image recognition", "object detection", "convolutional neural network", "cnn",
                "image segmentation", "facial recognition", "pose estimation", "optical character recognition", "ocr",
                "image classification", "feature detection", "edge detection", "image enhancement",
                "image restoration", "image generation", "video analysis", "motion detection",
                "scene understanding", "3d reconstruction", "depth estimation",
                
                # Generative AI
                "generative ai", "gan", "generative adversarial network", "diffusion", "diffusion model",
                "transformer", "large language model", "llm", "stable diffusion", "text-to-image",
                "deepfake", "synthetic data", "data augmentation", "content generation", "creative ai",
                "gpt", "bert", "t5", "autoencoder", "variational autoencoder", "vae",
                "style transfer", "image synthesis", "text-to-speech", "voice synthesis", "music generation",
                
                # ML Algorithms and Methods
                "classification", "clustering", "regression", "anomaly detection", "recommendation system",
                "decision tree", "random forest", "gradient boosting", "xgboost", "lightgbm", "catboost",
                "svm", "support vector machine", "k-means", "hierarchical clustering", "dbscan",
                "lstm", "long short-term memory", "rnn", "recurrent neural network", "attention mechanism",
                "transformer architecture", "self-attention", "bayesian network", "markov model",
                "ensemble learning", "bagging", "boosting", "stacking", "dimensionality reduction",
                "pca", "principal component analysis", "t-sne", "umap", "automl",
                
                # AI Ethics and Responsible AI
                "explainable ai", "xai", "interpretable ai", "ai ethics", "ai bias", "ai fairness",
                "responsible ai", "ai transparency", "ai accountability", "ai governance",
                "ai safety", "ai alignment", "ai robustness", "ai security"
            ]
        },
        {
            "id": 2,
            "name": "2-Human-Computer Interaction",
            "keywords": [
                # Brain-Computer Interfaces
                "brain-computer interface", "bci", "eeg", "electroencephalography", "brain signal", 
                "neural interface", "brain-machine interface", "bmi", "neurofeedback", "neuromodulation",
                "neural implant", "invasive bci", "non-invasive bci", "ssvep", "p300", "motor imagery",
                "brain-controlled", "mind-controlled", "neural recording", "neural decoding",
                "neural prosthetics", "neuroprosthetics", "neurorehabilitation", "brain mapping",
                
                # User Experience and Interface Design
                "user experience", "ux", "user interface", "ui", "usability", "user study", "hci",
                "human-computer interaction", "interaction design", "user-centered design", "ucd",
                "user research", "usability testing", "a/b testing", "wireframe", "prototype",
                "information architecture", "user journey", "user flow", "customer experience", "cx",
                "accessibility", "inclusive design", "responsive design", "mobile-first", "design system",
                "design thinking", "service design", "interaction pattern", "dark pattern", "ux writing",
                "microcopy", "user persona", "user story", "user feedback", "design critique",
                
                # AR/VR/XR
                "augmented reality", "virtual reality", "ar", "vr", "mixed reality", "mr", "extended reality", "xr",
                "immersive", "immersive experience", "immersive technology", "3d interface", "3d interaction",
                "head-mounted display", "hmd", "head-up display", "hud", "spatial computing",
                "spatial interface", "vr headset", "ar glasses", "smart glasses", "haptic feedback",
                "motion tracking", "eye tracking", "gaze interaction", "gesture recognition", "hand tracking",
                "volumetric display", "hologram", "holographic", "metaverse", "virtual environment",
                "virtual world", "digital twin", "telepresence", "teleoperation", "immersive learning",
                
                # Human Factors and Interaction
                "human factors", "ergonomics", "cognitive ergonomics", "physical ergonomics",
                "multimodal interaction", "gesture control", "voice interface", "speech interface",
                "conversational interface", "natural user interface", "nui", "tangible user interface", "tui",
                "wearable", "wearable technology", "wearable interface", "wearable computing",
                "haptic", "haptic interface", "force feedback", "tactile feedback", "vibrotactile",
                "adaptive interface", "context-aware interface", "personalized interface",
                "accessible design", "cognitive load", "mental model", "human error", "user error",
                "embodied interaction", "spatial interaction", "proxemic interaction",
                "social computing", "collaborative interface", "shared workspace"
            ]
        },
        {
            "id": 3,
            "name": "3-Big Data and Data Analytics",
            "keywords": [
                # Data Mining and Knowledge Discovery
                "data mining", "knowledge discovery", "pattern recognition", "association rules",
                "frequent pattern mining", "sequential pattern mining", "outlier detection",
                "anomaly detection", "cluster analysis", "classification", "prediction", "regression",
                "feature selection", "dimensionality reduction", "text mining", "web mining",
                "social media mining", "process mining", "graph mining", "network analysis",
                
                # Data Visualization and Analytics
                "data visualization", "visual analytics", "dashboard", "information visualization",
                "infographic", "chart", "graph", "plot", "interactive visualization", "exploratory visualization",
                "explainable visualization", "geovisualization", "map visualization", "scientific visualization",
                "visual data mining", "visual analytics dashboard", "storytelling with data",
                "data presentation", "data journalism", "visual exploration", "visual representation",
                
                # Big Data Systems and Processing
                "hadoop", "spark", "map reduce", "distributed computing", "data processing",
                "batch processing", "stream processing", "real-time analytics", "real-time processing",
                "distributed database", "nosql", "mongodb", "cassandra", "hbase", "redis",
                "data integration", "data ingestion", "data transformation", "data quality",
                "data cleaning", "data wrangling", "data preparation", "data profiling",
                "parallelization", "distributed algorithm", "distributed storage", "fault tolerance",
                
                # Time Series and Temporal Analysis
                "time series", "forecasting", "trend analysis", "temporal data", "sequence analysis",
                "time series forecasting", "seasonal analysis", "seasonality", "trend detection",
                "temporal pattern", "temporal clustering", "temporal association", "temporal prediction",
                "change point detection", "anomaly detection in time series", "multivariate time series",
                "time series classification", "arima", "sarima", "prophet", "exponential smoothing",
                
                # Data Management and Architecture
                "big data", "data warehouse", "data lake", "data lakehouse", "data mesh", "data fabric",
                "etl", "extract transform load", "elt", "extract load transform", "data pipeline",
                "data flow", "data governance", "data catalog", "data dictionary", "metadata management",
                "master data management", "mdm", "data modeling", "data architecture", "data strategy",
                "data inventory", "data lineage", "data provenance", "data versioning", "data lifecycle",
                
                # Business Intelligence and Analytics
                "business intelligence", "bi", "olap", "online analytical processing", "oltp",
                "descriptive analytics", "predictive analytics", "prescriptive analytics", "diagnostic analytics",
                "data science", "statistical analysis", "multivariate analysis", "correlation analysis",
                "regression analysis", "hypothesis testing", "a/b testing", "experimental design",
                "kpi", "key performance indicator", "metric", "performance measurement", "benchmark",
                "business analytics", "marketing analytics", "customer analytics", "operational analytics",
                "sales analytics", "financial analytics", "risk analytics", "supply chain analytics",
                "competitive intelligence", "data-driven decision making", "analytics maturity"
            ]
        },
        {
            "id": 4,
            "name": "4-Cyber Security",
            "keywords": [
                # Encryption and Cryptography
                "encryption", "cryptography", "cipher", "cryptanalysis", "secure communication",
                "symmetric encryption", "asymmetric encryption", "public key", "private key", "key exchange",
                "digital signature", "hash function", "md5", "sha", "aes", "rsa", "ecc", "elliptic curve",
                "quantum cryptography", "post-quantum cryptography", "homomorphic encryption",
                "zero-knowledge proof", "secure key management", "key distribution", "pki",
                "tls", "ssl", "https", "secure channel", "end-to-end encryption", "e2ee",
                
                # Secure Software Development
                "secure software", "software security", "code analysis", "vulnerability assessment",
                "static analysis", "dynamic analysis", "fuzz testing", "penetration testing", "pen testing",
                "secure coding", "secure design", "security by design", "threat modeling", "risk assessment",
                "secure sdlc", "devsecops", "security testing", "security review", "code review",
                "security standards", "security compliance", "security certification", "security verification",
                "security vulnerability", "security patch", "security update", "security maintenance",
                
                # Network Security
                "network security", "firewall", "intrusion detection", "intrusion prevention", "ids", "ips",
                "network monitoring", "traffic analysis", "packet inspection", "deep packet inspection",
                "network protection", "network defense", "perimeter security", "defense in depth",
                "dmz", "demilitarized zone", "vpn", "virtual private network", "proxy", "reverse proxy",
                "gateway security", "router security", "switch security", "network segmentation",
                "network isolation", "network access control", "nac", "network visibility",
                
                # Authentication and Access Control
                "authentication", "authorization", "access control", "identity management", "multi-factor",
                "two-factor authentication", "2fa", "mfa", "single sign-on", "sso", "federated identity",
                "oauth", "openid connect", "saml", "kerberos", "ldap", "active directory",
                "identity provider", "idp", "password management", "credential management",
                "biometric authentication", "fingerprint", "facial recognition", "iris scan",
                "behavioral biometrics", "passwordless authentication", "zero trust", "least privilege",
                "role-based access control", "rbac", "attribute-based access control", "abac",
                
                # Digital Forensics and Incident Response
                "forensics", "digital forensics", "incident response", "malware analysis", "threat intelligence",
                "threat hunting", "threat detection", "threat prevention", "threat response", "threat mitigation",
                "security incident", "security breach", "data breach", "data leak", "data loss",
                "forensic investigation", "forensic analysis", "forensic evidence", "forensic recovery",
                "chain of custody", "legal hold", "e-discovery", "incident handling", "incident management",
                "security operations", "security monitoring", "security analytics", "security intelligence",
                
                # Security Management and Compliance
                "security protocol", "security policy", "security procedure", "security standard",
                "security framework", "security governance", "security compliance", "security regulation",
                "security audit", "security assessment", "security certification", "security accreditation",
                "risk assessment", "risk management", "vulnerability management", "patch management",
                "security awareness", "security training", "security education", "security culture",
                "privacy", "data protection", "gdpr", "hipaa", "pci dss", "nist", "iso 27001",
                "sox", "regulatory compliance", "security metrics", "security kpi", "security maturity"
            ]
        },
        {
            "id": 5,
            "name": "5-Network and Distributed Systems",
            "keywords": [
                # 5G and Next Generation Networks
                "5g", "next generation network", "wireless network", "mobile network", "telecommunication",
                "6g", "network slicing", "massive mimo", "millimeter wave", "mmwave", "beamforming",
                "small cell", "ultra-reliable low latency", "urllc", "enhanced mobile broadband", "embb",
                "massive machine type communication", "mmtc", "radio access network", "ran",
                "open ran", "vran", "core network", "mobile edge computing", "software defined radio",
                "spectrum sharing", "network function", "service orchestration", "network automation",
                "network programmability", "network virtualization", "network energy efficiency",
                
                # Cloud Computing
                "cloud computing", "iaas", "infrastructure as a service", "paas", "platform as a service",
                "saas", "software as a service", "faas", "function as a service", "serverless",
                "virtualization", "container", "docker", "kubernetes", "k8s", "container orchestration",
                "microservice", "microservice architecture", "service mesh", "api gateway",
                "cloud native", "cloud migration", "cloud optimization", "cloud security", "cloud compliance",
                "multi-cloud", "hybrid cloud", "private cloud", "public cloud", "community cloud",
                "cloud storage", "cloud database", "cloud networking", "cloud monitoring", "cloud management",
                "infrastructure as code", "iac", "terraform", "ansible", "chef", "puppet",
                
                # Blockchain and Distributed Ledger
                "blockchain", "distributed ledger", "smart contract", "cryptocurrency", "consensus algorithm",
                "bitcoin", "ethereum", "solana", "hyperledger", "dlt", "distributed ledger technology",
                "proof of work", "pow", "proof of stake", "pos", "mining", "blockchain mining",
                "digital currency", "token", "tokenization", "tokenomics", "defi", "decentralized finance",
                "nft", "non-fungible token", "dao", "decentralized autonomous organization",
                "web3", "dapp", "decentralized application", "blockchain scalability", "blockchain interoperability",
                "private blockchain", "public blockchain", "permissioned blockchain", "permissionless blockchain",
                
                # P2P and Decentralized Systems
                "p2p", "peer-to-peer", "decentralized", "distributed system", "distributed computing",
                "distributed database", "distributed storage", "distributed file system", "mesh network",
                "ad hoc network", "self-organizing network", "overlay network", "distributed hash table", "dht",
                "distributed consensus", "byzantine fault tolerance", "bft", "paxos", "raft",
                "distributed coordination", "distributed synchronization", "distributed transaction",
                "decentralized identity", "did", "self-sovereign identity", "federated system",
                
                # Edge Computing and IoT
                "edge computing", "fog computing", "mist computing", "edge intelligence", "edge analytics",
                "edge ai", "iot", "internet of things", "industrial iot", "iiot", "sensor network",
                "m2m", "machine-to-machine", "smart device", "connected device", "embedded system",
                "low-power wide-area network", "lpwan", "lora", "sigfox", "nbiot", "narrow band iot",
                "mqtt", "coap", "device management", "device provisioning", "device security",
                "sensor fusion", "sensor data", "telemetry", "remote monitoring", "remote control",
                
                # Advanced Computing Paradigms
                "distributed computing", "parallel computing", "grid computing", "cluster computing",
                "high performance computing", "hpc", "quantum computing", "quantum network",
                "quantum internet", "quantum communication", "quantum cryptography",
                "neuromorphic computing", "brain-inspired computing", "in-memory computing",
                "optical computing", "dna computing", "biological computing", "molecular computing",
                "exascale computing", "supercomputing", "reconfigurable computing", "fpga"
            ]
        }
    ]
    
    scores = []
    for category in categories:
        score = 0
        matched_keywords = []
        
        for article_keyword in keywords:
            article_keyword_lower = article_keyword.lower()
            
            # Doğrudan eşleşme kontrol et
            if article_keyword_lower in category["keywords"]:
                score += 3  # Tam eşleşmeler daha yüksek puan alır
                matched_keywords.append(article_keyword)
            else:
                # Kısmi eşleşme kontrol et
                for category_keyword in category["keywords"]:
                    if article_keyword_lower in category_keyword or category_keyword in article_keyword_lower:
                        score += 1  # Kısmi eşleşmeler daha düşük puan alır
                        matched_keywords.append(article_keyword)
                        break
        
        scores.append({
            "category_id": category["id"],
            "category_name": category["name"],
            "score": score,
            "matched_keywords": list(set(matched_keywords))  # Tekrarlanan eşleşmeleri kaldır
        })
    
    if not scores:
        return None, []
        
    sorted_scores = sorted(scores, key=lambda x: x["score"], reverse=True)
    
    if sorted_scores[0]["score"] == 0:
        return None, []
        
    return sorted_scores[0]["category_name"], sorted_scores[0]["matched_keywords"]