# 🤖 Claude Integration Service  

A high-performance **FastAPI-based service** for integrating with **Anthropic's Claude AI**, designed for **efficient text processing** with:  

✅ **Asynchronous Queue Management** – Handles multiple requests efficiently.  
✅ **Rate Limiting** – Prevents API overuse and ensures smooth operation.  
✅ **Callback Dispatching** – Sends results to specified endpoints in real time.  
✅ **Scalable & Robust** – Built with FastAPI for speed and reliability.  

🔗 **GitHub Repository:** [Claude Integration Service](https://github.com/rebumatadele/Claude-Integration-Service)  

---

## 🚀 Features  

- **🔄 Async Processing:** Uses background tasks for smooth request handling.  
- **⚡ Optimized Queue Management:** Prevents blocking and prioritizes tasks efficiently.  
- **🛡️ Rate Limiting:** Ensures API calls remain within defined limits.  
- **🔔 Callback System:** Notifies clients with processed responses.  
- **📡 Webhook Support:** Allows seamless integration with external services.  
- **🛠️ Well-Structured MCP (Modular Clean Project):** Ensures maintainability and scalability.  

---

## 🔧 Installation & Setup  

### 🖥️ Running Locally  

1. **Clone the repository:**  
   ```bash
   git clone https://github.com/rebumatadele/Claude-Integration-Service.git
   cd Claude-Integration-Service
   ```

2. **Create and activate a virtual environment:**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the FastAPI server:**  
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **API Documentation:**  
   - Open your browser and navigate to:  
     - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)  
     - Redoc UI: [http://localhost:8000/redoc](http://localhost:8000/redoc)  

---

## 🛠 Configuration  

Ensure you have the correct API keys and environment variables set. You can configure them in a **.env** file:  

```env
ANTHROPIC_API_KEY=your_claude_api_key
RATE_LIMIT=5  # Example rate limit per second
CALLBACK_URL=https://your-callback-endpoint.com
```

---

## 📜 API Endpoints  

### **1️⃣ Process Text via Claude AI**  
- **Endpoint:** `POST /process`  
- **Description:** Sends a request to Claude AI and returns the response asynchronously.  
- **Example Request:**  
  ```json
  {
    "text": "What is the meaning of life?",
    "callback_url": "https://your-callback-endpoint.com"
  }
  ```
- **Response:**  
  ```json
  {
    "task_id": "123456",
    "status": "processing"
  }
  ```

### **2️⃣ Check Task Status**  
- **Endpoint:** `GET /status/{task_id}`  
- **Description:** Retrieves the status of a queued task.  

### **3️⃣ Health Check**  
- **Endpoint:** `GET /health`  
- **Description:** Returns service health status.  

---

## 🔥 Deployment  

### **Docker Setup**  
1. **Build the Docker Image:**  
   ```bash
   docker build -t claude-integration-service .
   ```
2. **Run the Container:**  
   ```bash
   docker run -p 8000:8000 --env-file .env claude-integration-service
   ```

---

## 📜 License  

This project is licensed under the **MIT License**.  

---

## 🙌 Contributing  

We welcome contributions! Feel free to fork the repo, open issues, or submit pull requests.  

---

## 📩 Contact  

For inquiries or collaboration:  
🔗 **GitHub:** [Rebuma Tadele](https://github.com/rebumatadele)  

Let’s build smarter AI integrations together! 🚀🤖
