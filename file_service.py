import boto3
import os
import mimetypes
import uuid
from dotenv import load_dotenv

load_dotenv()

# OCI Object Storage configuration
oci_namespace = os.getenv("OCI_NAMESPACE")  # OCI 네임스페이스
oci_region = os.getenv("OCI_REGION")  # 리전
oci_endpoint = f"https://{oci_namespace}.compat.objectstorage.{oci_region}.oraclecloud.com"
oci_access_key_id = os.getenv("OCI_ACCESS_KEY") # Replace with your OCI Customer Secret Key Access Key ID
oci_secret_access_key = os.getenv("OCI_SECRET_KEY") # Replace with your OCI Customer Secret Key Secret Access Key
bucket_name = os.getenv("OCI_BUCKET") # Replace with your OCI bucket name

# 환경변수 검증
if not all([oci_namespace, oci_access_key_id, oci_secret_access_key, bucket_name]):
    raise RuntimeError("OCI 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# Create an S3 client for OCI Object Storage
s3_client = boto3.client(
    's3',
    endpoint_url=oci_endpoint,
    aws_access_key_id=oci_access_key_id,
    aws_secret_access_key=oci_secret_access_key
)

def upload_file_to_oci(local_file_path: str) -> str:
    """
    로컬 파일을 OCI Object Storage에 업로드하고 공개 URL을 반환합니다.
    
    Args:
        local_file_path (str): 업로드할 로컬 파일의 경로
    
    Returns:
        str: 업로드된 파일의 공개 웹 엔드포인트 URL
    
    Raises:
        FileNotFoundError: 로컬 파일이 존재하지 않는 경우
        ValueError: 지원되지 않는 파일 형식인 경우
        RuntimeError: 업로드 실패 시
    """
    # 파일 존재 확인
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {local_file_path}")
    
    # 파일 정보 추출
    file_name = os.path.basename(local_file_path)
    file_extension = os.path.splitext(file_name)[1].lower()
    
    # 지원되는 이미지 형식 확인
    supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
    if file_extension not in supported_extensions:
        raise ValueError(f"지원되지 않는 파일 형식입니다: {file_extension}. 지원 형식: {', '.join(supported_extensions)}")
    
    # MIME 타입 결정
    content_type, _ = mimetypes.guess_type(local_file_path)
    if not content_type:
        # 기본 MIME 타입 매핑
        mime_mapping = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        content_type = mime_mapping.get(file_extension, 'application/octet-stream')
    
    # 객체 이름 생성 (UUID 기반으로 자동 생성)
    unique_id = str(uuid.uuid4())
    object_name = f"images/{unique_id}{file_extension}"
    
    try:
        # 파일 크기 확인
        file_size = os.path.getsize(local_file_path)
        print(f"업로드 시작: {file_name} ({file_size} bytes)")
        
        # 파일 업로드
        with open(local_file_path, 'rb') as f:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_name,
                Body=f,
                ContentType=content_type
            )
        
        # 공개 URL 생성
        public_url = f"https://objectstorage.{oci_region}.oraclecloud.com/n/{oci_namespace}/b/{bucket_name}/o/{object_name}"
        
        print(f"파일 업로드 성공: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"파일 업로드 실패: {e}")
        raise RuntimeError(e)

