import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch, RunnableLambda
from langchain_groq import ChatGroq

# --- 1. SETUP ---
# Muat environment variables dari .env
load_dotenv()

# Inisialisasi model LLM dari Groq
# Pastikan GROQ_API_KEY sudah ada di file .env
llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")

# --- 2. PROMPT TEMPLATES & DESTINATIONS ---
# Ini adalah "pengetahuan" yang ditanamkan ke masing-masing agent
order_template = """
Anda adalah CS virtual spesialis pesanan. Anda ramah dan akurat.
Gunakan informasi di bawah ini untuk menjawab:
- Pelacakan pesanan bisa dilakukan via link di email konfirmasi.
- Estimasi pengiriman Jabodetabek adalah 2-3 hari kerja.
- Pengembalian barang bisa dilakukan maksimal 7 hari setelah barang diterima.

ATURAN PENTING: Jawab HANYA pertanyaan seputar pesanan. Jika user bertanya tentang pesanan TAPI juga menyebutkan kata 'tagihan' atau 'pembayaran', JANGAN MENEBAK. Katakan dengan sopan bahwa Anda hanya bisa membantu soal pesanan, dan untuk info tagihan bisa ditanyakan di sesi chat terpisah.

Pertanyaan: {input}
Jawaban:
"""

billing_template = """
Anda adalah CS virtual spesialis tagihan (billing). Anda to the point dan profesional.
Gunakan informasi di bawah ini untuk menjawab:
- Tagihan dikirim setiap tanggal 1 tiap bulan.
- Metode pembayaran yang diterima: Transfer Bank, Kartu Kredit.
- Jatuh tempo pembayaran adalah tanggal 20 setiap bulan.

ATURAN PENTING: Jawab HANYA pertanyaan seputar tagihan. Jika user bertanya tentang tagihan TAPI juga menyebutkan kata 'pesanan' atau 'pengiriman', JANGAN MENEBAK. Katakan dengan sopan bahwa Anda hanya bisa membantu soal tagihan, dan untuk info pesanan bisa ditanyakan di sesi chat terpisah.

Pertanyaan: {input}
Jawaban:
"""

# --- 3. ROUTER CHAIN ---
# Prompt untuk router
destinations = "order: Baik untuk pertanyaan tentang status pesanan, pengiriman, dan pelacakan\nbilling: Baik untuk pertanyaan tentang tagihan, faktur, dan pembayaran"
router_template = f"""
Anda adalah AI yang bertugas mengarahkan pertanyaan user ke agent yang tepat.
Pilih salah satu dari agent berikut ini yang paling sesuai dengan pertanyaan user:
{destinations}
Hanya kembalikan NAMA agent yang dipilih, tidak ada teks lain.
Jika tidak ada yang cocok, kembalikan 'DEFAULT'.
Pertanyaan User: {{input}}
Pilihan Agent:
"""
router_prompt = ChatPromptTemplate.from_template(router_template)

# Chain 1: Router Chain
# Ini adalah chain yang tugasnya memilih agent ("order", "billing", atau "default")
router_chain = router_prompt | llm | StrOutputParser()

# Chain 2: Destination Chains
# Ini adalah chain untuk masing-masing agent
order_prompt = ChatPromptTemplate.from_template(order_template)
order_chain = (
    order_prompt 
    | llm 
    | StrOutputParser()
    | RunnableLambda(lambda text: {"source_agent": "Agent Order", "response": text})
)

billing_prompt = ChatPromptTemplate.from_template(billing_template)
billing_chain = (
    billing_prompt 
    | llm 
    | StrOutputParser()
    | RunnableLambda(lambda text: {"source_agent": "Agent Billing", "response": text})
)

# Chain 3: Default Chain (Eskalasi)
default_response_text = "Maaf, saya kurang mengerti. Saya akan sambungkan Anda ke tim Customer Service."
default_chain = RunnableLambda(
    lambda x: {"source_agent": "Eskalasi ke CS Manusia", "response": default_response_text}
)

# Menggabungkan semuanya dengan RunnableBranch
# Logikanya: "Jika output dari router_chain adalah 'order', maka jalankan order_chain. Jika 'billing', jalankan billing_chain. Jika tidak keduanya, jalankan default_chain."
branch = RunnableBranch(
    (lambda x: "order" in x["topic"].lower(), order_chain),
    (lambda x: "billing" in x["topic"].lower(), billing_chain),
    default_chain,
)

# Membuat Rantai Lengkap (Full Chain)
# 1. Input user masuk.
# 2. `router_chain` dijalankan untuk menentukan `topic`.
# 3. `branch` dijalankan, menggunakan `topic` untuk memilih chain yang benar.
full_chain = {"topic": router_chain, "input": lambda x: x["input"]} | branch

# --- 4. API DENGAN FASTAPI ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def handle_chat(request: ChatRequest):
    response = full_chain.invoke({"input": request.message})
    return response