import os
import chromadb
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

class LocalChromaDB:
    def __init__(self):
        self.CHROMA_PATH = "data/chromadb"
        # Modelo multilingüe optimizado para temas técnicos y urbanismo
        self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.client = chromadb.PersistentClient(path=self.CHROMA_PATH)
        # NOMBRE UNIFICADO: conocimiento_siniestralidad
        self.collection = self.client.get_or_create_collection(name="conocimiento_siniestralidad")

    def procesar_pdf(self, ruta_pdf):
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() + "\n"
        
        # Chunks de 800 con traslape para no perder contexto de normas del POT
        chunk_size = 800
        overlap = 100
        chunks = [texto_completo[i : i + chunk_size] for i in range(0, len(texto_completo), chunk_size - overlap)]
        return chunks

    def alimentar_base_datos(self, carpeta_pdfs):
        if not os.path.exists(carpeta_pdfs):
            os.makedirs(carpeta_pdfs)
            print(f"Carpeta {carpeta_pdfs} creada. Mete tus PDFs ahí.")
            return

        for archivo in os.listdir(carpeta_pdfs):
            if archivo.endswith(".pdf"):
                chunks = self.procesar_pdf(os.path.join(carpeta_pdfs, archivo))
                ids = [f"{archivo}_{i}" for i in range(len(chunks))]
                metadatas = [{"fuente": archivo, "localidad": "Kennedy/Patio Bonito"} for _ in range(len(chunks))]
                embeddings = self.model.encode(chunks).tolist()

                self.collection.add(
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas,
                    ids=ids
                )
        print("✅ Base de datos 'conocimiento_siniestralidad' lista y persistida.")

if __name__ == "__main__":
    db = LocalChromaDB()
    db.alimentar_base_datos("documentos")