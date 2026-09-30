"""Seed taxonomy of standard technology skills with aliases and categories."""

from typing import TypedDict


class TaxonomyEntry(TypedDict):
    name: str
    category: str
    aliases: list[str]


SEED_TAXONOMY: list[TaxonomyEntry] = [
    # --- Languages ---
    {
        "name": "Python",
        "category": "Languages",
        "aliases": ["python3", "python 3", "py"],
    },
    {
        "name": "Java",
        "category": "Languages",
        "aliases": ["java core", "core java", "java 8", "java 17", "java 21"],
    },
    {
        "name": "JavaScript",
        "category": "Languages",
        "aliases": ["js", "vanilla javascript", "es6", "es2020", "ecmascript"],
    },
    {"name": "TypeScript", "category": "Languages", "aliases": ["ts"]},
    {
        "name": "C++",
        "category": "Languages",
        "aliases": ["cpp", "c plus plus", "c/c++"],
    },
    {"name": "C", "category": "Languages", "aliases": ["ansi c", "c language"]},
    {
        "name": "C#",
        "category": "Languages",
        "aliases": ["csharp", "c-sharp", ".net c#"],
    },
    {"name": "Go", "category": "Languages", "aliases": ["golang", "go language"]},
    {"name": "Rust", "category": "Languages", "aliases": ["rust-lang", "rustlang"]},
    {"name": "Ruby", "category": "Languages", "aliases": ["ruby-lang"]},
    {"name": "PHP", "category": "Languages", "aliases": ["php 8", "php7"]},
    {"name": "Swift", "category": "Languages", "aliases": ["swiftlang", "apple swift"]},
    {"name": "Kotlin", "category": "Languages", "aliases": ["kotlin/android"]},
    {"name": "Scala", "category": "Languages", "aliases": ["scala-lang"]},
    {
        "name": "SQL",
        "category": "Languages",
        "aliases": ["ansi sql", "structured query language"],
    },
    {
        "name": "R",
        "category": "Languages",
        "aliases": ["r-lang", "r language", "r programming"],
    },
    {
        "name": "Bash",
        "category": "Languages",
        "aliases": ["shell scripting", "bash scripting", "sh", "zsh"],
    },
    {"name": "HTML/CSS", "category": "Languages", "aliases": ["html", "html5", "css"]},
    # --- Frameworks & Web Libraries ---
    {"name": "FastAPI", "category": "Frameworks", "aliases": ["fast-api"]},
    {
        "name": "Django",
        "category": "Frameworks",
        "aliases": ["django framework", "drf", "django rest framework"],
    },
    {"name": "Flask", "category": "Frameworks", "aliases": ["flask framework"]},
    {"name": "React", "category": "Frameworks", "aliases": ["reactjs", "react.js"]},
    {
        "name": "Next.js",
        "category": "Frameworks",
        "aliases": ["nextjs", "next.js framework"],
    },
    {"name": "Vue.js", "category": "Frameworks", "aliases": ["vue", "vuejs"]},
    {"name": "Angular", "category": "Frameworks", "aliases": ["angularjs"]},
    {"name": "Node.js", "category": "Frameworks", "aliases": ["nodejs", "node"]},
    {
        "name": "Express.js",
        "category": "Frameworks",
        "aliases": ["express", "expressjs"],
    },
    {
        "name": "Spring Boot",
        "category": "Frameworks",
        "aliases": ["springboot", "spring-boot", "spring framework"],
    },
    {
        "name": "ASP.NET Core",
        "category": "Frameworks",
        "aliases": ["asp.net", "dotnet core", ".net core"],
    },
    {"name": "Ruby on Rails", "category": "Frameworks", "aliases": ["rails", "ror"]},
    {"name": "Tailwind CSS", "category": "Frameworks", "aliases": ["tailwindcss"]},
    {"name": "GraphQL", "category": "Frameworks", "aliases": ["graphql api", "gql"]},
    {
        "name": "REST APIs",
        "category": "Frameworks",
        "aliases": ["restful apis", "rest", "rest api design"],
    },
    {
        "name": "gRPC",
        "category": "Frameworks",
        "aliases": ["protobuf", "grpc services"],
    },
    # --- Databases & Storage ---
    {
        "name": "PostgreSQL",
        "category": "Databases",
        "aliases": ["postgres", "pgsql", "psql", "postgres database"],
    },
    {"name": "MySQL", "category": "Databases", "aliases": ["mysql server", "mariadb"]},
    {"name": "SQLite", "category": "Databases", "aliases": ["sqlite3"]},
    {"name": "MongoDB", "category": "Databases", "aliases": ["mongo", "mongodb atlas"]},
    {
        "name": "Redis",
        "category": "Databases",
        "aliases": ["redis cache", "redis in-memory"],
    },
    {"name": "Cassandra", "category": "Databases", "aliases": ["apache cassandra"]},
    {
        "name": "Elasticsearch",
        "category": "Databases",
        "aliases": ["elastic search", "opensearch", "elk stack"],
    },
    {"name": "DynamoDB", "category": "Databases", "aliases": ["aws dynamodb"]},
    {"name": "Snowflake", "category": "Databases", "aliases": ["snowflake dw"]},
    {
        "name": "BigQuery",
        "category": "Databases",
        "aliases": ["google bigquery", "gbq"],
    },
    {"name": "Neo4j", "category": "Databases", "aliases": ["graph database neo4j"]},
    {"name": "SQLAlchemy", "category": "Databases", "aliases": ["sql alchemy"]},
    # --- Cloud & DevOps ---
    {
        "name": "Kubernetes",
        "category": "Cloud & DevOps",
        "aliases": ["k8s", "kube", "kubernetes orchestration", "k8s orchestration"],
    },
    {
        "name": "Docker",
        "category": "Cloud & DevOps",
        "aliases": ["docker containers", "containerization", "docker compose"],
    },
    {
        "name": "Amazon Web Services",
        "category": "Cloud & DevOps",
        "aliases": ["aws", "amazon cloud", "aws cloud"],
    },
    {
        "name": "Google Cloud Platform",
        "category": "Cloud & DevOps",
        "aliases": ["gcp", "google cloud"],
    },
    {
        "name": "Microsoft Azure",
        "category": "Cloud & DevOps",
        "aliases": ["azure", "azure cloud"],
    },
    {
        "name": "Terraform",
        "category": "Cloud & DevOps",
        "aliases": ["hashicorp terraform", "infrastructure as code", "iac"],
    },
    {"name": "Ansible", "category": "Cloud & DevOps", "aliases": ["red hat ansible"]},
    {
        "name": "CI/CD",
        "category": "Cloud & DevOps",
        "aliases": ["continuous integration", "continuous delivery", "ci cd"],
    },
    {
        "name": "GitHub Actions",
        "category": "Cloud & DevOps",
        "aliases": ["gh actions", "github ci"],
    },
    {"name": "GitLab CI", "category": "Cloud & DevOps", "aliases": ["gitlab ci/cd"]},
    {"name": "Jenkins", "category": "Cloud & DevOps", "aliases": ["jenkins ci"]},
    {
        "name": "Linux",
        "category": "Cloud & DevOps",
        "aliases": ["unix", "ubuntu", "debian", "linux sysadmin"],
    },
    {
        "name": "Prometheus",
        "category": "Cloud & DevOps",
        "aliases": ["prometheus metrics"],
    },
    {
        "name": "Grafana",
        "category": "Cloud & DevOps",
        "aliases": ["grafana dashboards"],
    },
    {
        "name": "Nginx",
        "category": "Cloud & DevOps",
        "aliases": ["nginx reverse proxy"],
    },
    {
        "name": "Git",
        "category": "Cloud & DevOps",
        "aliases": ["version control", "github"],
    },
    # --- Machine Learning & Data Science ---
    {
        "name": "Machine Learning",
        "category": "Machine Learning",
        "aliases": ["ml", "machine learning algorithms"],
    },
    {
        "name": "Deep Learning",
        "category": "Machine Learning",
        "aliases": ["dl", "deep neural networks", "neural networks"],
    },
    {"name": "PyTorch", "category": "Machine Learning", "aliases": ["torch"]},
    {"name": "TensorFlow", "category": "Machine Learning", "aliases": ["tf"]},
    {"name": "Scikit-Learn", "category": "Machine Learning", "aliases": ["sklearn"]},
    {"name": "Keras", "category": "Machine Learning", "aliases": ["tf.keras"]},
    {
        "name": "Natural Language Processing",
        "category": "Machine Learning",
        "aliases": ["nlp", "text processing"],
    },
    {
        "name": "Computer Vision",
        "category": "Machine Learning",
        "aliases": ["cv", "opencv"],
    },
    {
        "name": "Large Language Models",
        "category": "Machine Learning",
        "aliases": ["llm", "llms", "foundation models"],
    },
    {
        "name": "Transformer Architecture",
        "category": "Machine Learning",
        "aliases": ["transformers", "attention mechanism"],
    },
    {
        "name": "Hugging Face",
        "category": "Machine Learning",
        "aliases": ["huggingface"],
    },
    {"name": "LangChain", "category": "Machine Learning", "aliases": ["langgraph"]},
    {"name": "Pandas", "category": "Machine Learning", "aliases": ["pandas library"]},
    {"name": "NumPy", "category": "Machine Learning", "aliases": ["numpy arrays"]},
    {
        "name": "Reinforcement Learning",
        "category": "Machine Learning",
        "aliases": ["rl"],
    },
    {
        "name": "Retrieval-Augmented Generation",
        "category": "Machine Learning",
        "aliases": ["rag", "rag pipelines", "vector search"],
    },
    # --- Data Engineering & Distributed Systems ---
    {
        "name": "Apache Spark",
        "category": "Data Engineering",
        "aliases": ["spark", "pyspark"],
    },
    {
        "name": "Apache Kafka",
        "category": "Data Engineering",
        "aliases": ["kafka", "event streaming"],
    },
    {"name": "RabbitMQ", "category": "Data Engineering", "aliases": ["amqp"]},
    {"name": "Airflow", "category": "Data Engineering", "aliases": ["apache airflow"]},
    {
        "name": "Distributed Systems",
        "category": "Data Engineering",
        "aliases": ["distributed computing"],
    },
    {"name": "Hadoop", "category": "Data Engineering", "aliases": ["hdfs"]},
    {"name": "dbt", "category": "Data Engineering", "aliases": ["data build tool"]},
    # --- Core Theory & Architecture ---
    {
        "name": "Data Structures & Algorithms",
        "category": "Theory & Architecture",
        "aliases": ["dsa", "algorithms", "data structures"],
    },
    {
        "name": "Object-Oriented Programming",
        "category": "Theory & Architecture",
        "aliases": ["oop", "object oriented design"],
    },
    {
        "name": "Microservices",
        "category": "Theory & Architecture",
        "aliases": ["microservice architecture"],
    },
    {
        "name": "System Design",
        "category": "Theory & Architecture",
        "aliases": ["software architecture", "hld"],
    },
    {
        "name": "Design Patterns",
        "category": "Theory & Architecture",
        "aliases": ["gang of four", "software design patterns"],
    },
    {
        "name": "Concurrency",
        "category": "Theory & Architecture",
        "aliases": ["multithreading", "parallel programming", "async programming"],
    },
    {
        "name": "Operating Systems",
        "category": "Theory & Architecture",
        "aliases": ["os internals", "processes and threads"],
    },
    {
        "name": "Computer Networks",
        "category": "Theory & Architecture",
        "aliases": ["networking", "tcp/ip", "http/https"],
    },
    {
        "name": "Database Design",
        "category": "Theory & Architecture",
        "aliases": ["schema design", "normalization"],
    },
    {
        "name": "Cybersecurity",
        "category": "Theory & Architecture",
        "aliases": ["security", "application security", "appsec"],
    },
    # --- Testing & Quality Assurance ---
    {
        "name": "Unit Testing",
        "category": "Testing & QA",
        "aliases": ["unit tests", "component testing"],
    },
    {
        "name": "Integration Testing",
        "category": "Testing & QA",
        "aliases": ["integration tests"],
    },
    {"name": "Test-Driven Development", "category": "Testing & QA", "aliases": ["tdd"]},
    {"name": "Pytest", "category": "Testing & QA", "aliases": ["pytest framework"]},
    {"name": "Jest", "category": "Testing & QA", "aliases": ["jest framework"]},
    {"name": "Cypress", "category": "Testing & QA", "aliases": ["cypress e2e"]},
]
