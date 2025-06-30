"""Document Processor

Processa arquivos PDF, CSV, planilhas Excel e Google Sheets enviados pelo usuário no Slack.
Integra com OpenAI File Search para análise de documentos.
"""

import logging
import os
import tempfile
import aiohttp
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Processa documentos enviados via Slack para análise com OpenAI."""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.supported_types = {
            'application/pdf': '.pdf',
            'text/csv': '.csv',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.google-apps.spreadsheet': '.xlsx',  # Google Sheets
            'application/vnd.google-apps.document': '.docx',    # Google Docs
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'text/plain': '.txt'
        }
    
    async def extract_document_files(self, event: Dict[str, Any], slack_client) -> List[Dict[str, Any]]:
        """Extrai arquivos de documentos de um evento do Slack."""
        document_files = []

        files = event.get("files", [])
        logger.info(f"🔍 DEBUG: Encontrados {len(files)} arquivos no evento")

        for file_info in files:
            mimetype = file_info.get("mimetype", "")
            filename = file_info.get("name", "")
            
            # Verifica se é um tipo de documento suportado
            if self._is_supported_document(mimetype, filename):
                try:
                    file_url = file_info.get("url_private")
                    if file_url:
                        # Obter informações do arquivo
                        response = await slack_client.api_call(
                            "files.info",
                            data={"file": file_info.get("id")}
                        )
                        
                        if response["ok"]:
                            document_files.append({
                                "name": filename,
                                "url": file_url,
                                "mimetype": mimetype,
                                "size": file_info.get("size", 0),
                                "id": file_info.get("id")
                            })
                            logger.info(f"Documento encontrado: {filename} ({mimetype})")
                except Exception as e:
                    logger.error(f"Erro ao processar documento {filename}: {e}")
        
        return document_files
    
    def _is_supported_document(self, mimetype: str, filename: str) -> bool:
        """Verifica se o arquivo é um documento suportado."""
        # Verifica por mimetype
        if mimetype in self.supported_types:
            return True
        
        # Verifica por extensão do arquivo
        filename_lower = filename.lower()
        supported_extensions = ['.pdf', '.csv', '.xls', '.xlsx', '.docx', '.doc', '.txt']
        
        # Verificar extensão normal
        file_extension = self._get_file_extension(filename).lower()
        if file_extension in supported_extensions:
            return True
        
        # Verificar formatos compostos como .docx.pdf
        for ext in supported_extensions:
            if filename_lower.endswith(ext):
                return True
        
        return False
    
    async def upload_to_openai(self, document_files: List[Dict[str, Any]], 
                              slack_token: str) -> List[Dict[str, Any]]:
        """Faz upload dos documentos para OpenAI e retorna informações dos arquivos."""
        uploaded_files = []
        
        for doc_file in document_files:
            try:
                logger.info(f"Fazendo upload do documento: {doc_file['name']}")
                
                # Download do arquivo do Slack
                file_content = await self._download_slack_file(
                    doc_file['url'], slack_token
                )
                
                if file_content:
                    # Upload para OpenAI
                    openai_file = await self._upload_to_openai_files(
                        file_content, doc_file['name']
                    )
                    
                    if openai_file:
                        uploaded_files.append({
                            'name': doc_file['name'],
                            'openai_file_id': openai_file.id,
                            'size': doc_file['size'],
                            'mimetype': doc_file['mimetype']
                        })
                        logger.info(f"✅ Upload concluído: {doc_file['name']} -> {openai_file.id}")
                    else:
                        logger.error(f"❌ Falha no upload para OpenAI: {doc_file['name']}")
                else:
                    logger.error(f"❌ Falha no download do Slack: {doc_file['name']}")
                    
            except Exception as e:
                logger.error(f"Erro ao processar {doc_file['name']}: {e}")
        
        return uploaded_files
    
    async def _download_slack_file(self, file_url: str, slack_token: str) -> Optional[bytes]:
        """Baixa um arquivo do Slack."""
        try:
            headers = {
                "Authorization": f"Bearer {slack_token}"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Erro ao baixar arquivo: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Erro no download do arquivo: {e}")
            return None
    
    async def _upload_to_openai_files(self, file_content: bytes, filename: str):
        """Faz upload de um arquivo para OpenAI Files API."""
        try:
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(filename)) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            try:
                # Upload para OpenAI
                with open(temp_file_path, 'rb') as file:
                    openai_file = await self.openai_client.files.create(
                        file=file,
                        purpose='assistants'
                    )
                return openai_file
            finally:
                # Limpar arquivo temporário
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Erro no upload para OpenAI: {e}")
            return None
    
    def _get_file_extension(self, filename: str) -> str:
        """Obtém a extensão do arquivo."""
        if '.' in filename:
            return '.' + filename.split('.')[-1]
        return '.txt'
    
    def _get_mime_type(self, filename: str) -> str:
        """Retorna o tipo MIME baseado na extensão do arquivo."""
        filename_lower = filename.lower()
        
        # Mapeamento de extensões para tipos MIME
        mime_types = {
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword'
        }
        
        # Verificar extensão normal primeiro
        ext = self._get_file_extension(filename).lower()
        if ext in mime_types:
            return mime_types[ext]
        
        # Verificar formatos compostos como .docx.pdf
        for extension, mime_type in mime_types.items():
            if filename_lower.endswith(extension):
                return mime_type
        
        return 'application/octet-stream'
    
    async def create_vector_store_with_files(self, uploaded_files: List[Dict[str, Any]], 
                                           store_name: str = "Documentos do Usuário") -> Optional[str]:
        """Cria uma vector store efêmera com os arquivos enviados."""
        try:
            if not uploaded_files:
                return None
            
            # Criar vector store efêmera com expiração de 1 dia
            vector_store = await self.openai_client.vector_stores.create(
                name=store_name,
                expires_after={
                    "anchor": "last_active_at",
                    "days": 1
                }
            )
            
            # Adicionar arquivos à vector store
            file_ids = [file_info['openai_file_id'] for file_info in uploaded_files]
            
            await self.openai_client.vector_stores.file_batches.create(
                vector_store_id=vector_store.id,
                file_ids=file_ids
            )
            
            logger.info(f"✅ Vector store criada: {vector_store.id} com {len(file_ids)} arquivos")
            return vector_store.id
            
        except Exception as e:
            logger.error(f"Erro ao criar vector store: {e}")
            return None
    
    async def add_files_to_existing_vector_store(self, vector_store_id: str, 
                                               uploaded_files: List[Dict[str, Any]]) -> Optional[str]:
        """Adiciona arquivos a uma vector store existente."""
        try:
            if not uploaded_files or not vector_store_id:
                return vector_store_id
            
            # Adicionar novos arquivos à vector store existente
            file_ids = [file_info['openai_file_id'] for file_info in uploaded_files]
            
            await self.openai_client.vector_stores.file_batches.create(
                vector_store_id=vector_store_id,
                file_ids=file_ids
            )
            
            logger.info(f"✅ Adicionados {len(file_ids)} arquivos ao vector store: {vector_store_id}")
            return vector_store_id
            
        except Exception as e:
            logger.error(f"Erro ao adicionar arquivos ao vector store {vector_store_id}: {e}")
            return None
    
    def format_upload_summary(self, uploaded_files: List[Dict[str, Any]]) -> str:
        """Formata um resumo dos arquivos enviados."""
        if not uploaded_files:
            return "❌ Nenhum documento foi processado com sucesso."
        
        # Formato simplificado: apenas o nome do arquivo processado
        if len(uploaded_files) == 1:
            return f"Processado: {uploaded_files[0]['name']}"
        else:
            file_names = [f['name'] for f in uploaded_files]
            return f"Processados: {', '.join(file_names)}"
    
    async def get_vector_store_file_count(self, vector_store_id: str) -> int:
        """Retorna o número de arquivos em uma vector store."""
        try:
            files = await self.openai_client.vector_stores.files.list(vector_store_id=vector_store_id)
            return len(files.data)
        except Exception as e:
            logger.error(f"Erro ao contar arquivos na vector store {vector_store_id}: {e}")
            return 0