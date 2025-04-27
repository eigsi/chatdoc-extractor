# :cyclone: ChatDoc Extractor

## :scroll: Description
**ChatDoc Extractor** is a tool that parses local PDF files containing unstructured information, uses ChatGPT to extract relevant data, and automatically loads that data into a database for easy querying and reuse.

## :pencil2: Install the project
### Prerequisites
Before getting started, ensure that you have the following installed on your system:
- [Docker](https://www.docker.com)
- [Python](https://www.python.org)

### Setup Instructions
#### 1 **Clone the Repository**
  Create an empty folder and init git
  ```html
  git init
  ```
  Link your folder to the GitHub repo
  ```html
  git remote add origin https://github.com/eigsi/chatdoc-extractor.git
  ```
  import the files from the repo
  ```html
  git pull origin main
  ```
#### 2 **Set Up a Virtual Environment**
  Create a virtual environment:
  ```html
  python -m venv venv
  ```
  Activate the virtual environment (MacOS, Linux)
  ```html
  source venv/bin/activate
  ```
Activate the virtual environment (Windows)
  ```html
  venv\Scripts\activate
  ```
#### 3 Install Dependencies
```html
pip install -r requirements.txt
```
#### 4 Create the dabatase with Docker
Make sure Docker is running on your machine.  
Use Docker Compose to start the PostgreSQL database and Adminer containers:
  ```html
  docker-compose up -d
  ```

## :memo: Usage
### 1 **Initialize the database and vector store
  ```html
  python3 initiate.py
  ```
### 2 *Extract data from your PDFs and load into the database
  ```html
  python3 main.py
  ```

## :books: The Stack (dev)
- **LangChain**  
- **SQL Alchemy** 
- **Chroma db**
- **OpenAI API**
- **Docker**