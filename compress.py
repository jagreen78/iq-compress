import re
import sys
import os
import uvicorn

from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image; 
import colorsys
from fastapi.middleware.cors import CORSMiddleware



CHARSET = ''.join([chr(i) for i in range(127)])
# 숫자 -> 문자 매핑
METHOD = {
    0: "RLE",
    1: "BASE7",
}
# 문자 -> 숫자 매핑
char_to_number = {
    " ": 0,
    "$": 1,
    "J": 2,
    "I": 3,
    "i": 4,
    ":": 5,
    "'": 6,
}

# 숫자 -> 문자 매핑
number_to_char = {
    0: " ",
    1: "$",
    2: "J",
    3: "I",
    4: "i",
    5: ":",
    6: "'",
}
# 텍스트를 숫자 문자열로 변환
def map_text_to_single_digit_numbers(text):
    result = []
    for char in text:
        # 각 문자가 매핑 딕셔너리에 있으면 해당 숫자로 바꿈
        if char in char_to_number:
            result.append(str(char_to_number[char]))
        else:
            result.append(str(0))
    
    return ''.join(result)
# 숫자 문자열을 텍스트로 변환
def map_numbers_to_text(number_string):
    result = []
    for num in number_string:
        # 숫자가 딕셔너리에 있으면 해당 문자로 바꿈
        if num.isdigit() and int(num) in number_to_char:
            result.append(number_to_char[int(num)])

    return ''.join(result)


# 7진수 -> 10진수 변환
def base7_to_base10(octal):
    return int(str(octal), 7)

def base10_to_base7(decimal):
    if decimal == 0:
        return "0"  # 0은 그대로 반환
    
    result = []
    while decimal > 0:
        result.append(str(decimal % 7))  # 나머지를 7진수로 변환
        decimal //= 7  # 몫을 구하여 계속 나눔
    
    return ''.join(reversed(result))  # 결과를 역순으로 반환

# charset 기반 변환. 
def decimal_to_base127(decimal):
    """십진수를 127진법으로 변환"""
    if decimal == 0:
        return CHARSET[0]
    
    base127_str = ''
    while decimal > 0:
        base127_str = CHARSET[decimal % len(CHARSET)] + base127_str
        decimal //=  len(CHARSET)
    return base127_str

# 127진법을 다시 10진수로 변환
def base127_to_decimal(base127_str):
    """127진법을 십진수로 변환"""
    decimal = 0
    for char in base127_str:
        decimal = decimal * 127 + CHARSET.index(char)
    return decimal



# 127진법으로 변환한 값을 원본 텍스트로 복원
def decode_from_base127(base127_str):
    decimal_value = base127_to_decimal(base127_str)
    return decimal_value
def rle_encode(data):
    """Run-Length Encoding (RLE) 압축 함수"""
    if not data:
        return [], []

    encoded_num = []
    encoded_text = []
    count = 1
    for i in range(1, len(data)):
        if data[i] == data[i - 1] and count < 9:
            count += 1  # 연속된 문자일 경우 카운트 증가
        else:
            encoded_num.append(count)
            encoded_text.append(data[i - 1])
            count = 1  # 카운트를 초기화

    # 마지막 문자 처리
    encoded_num.append(count)
    encoded_text.append(data[-1])
    return encoded_num , encoded_text

def make_rle_list(text):
    """텍스트를 암호화하는 함수"""
    # 1. 텍스트를 RLE로 압축
    encoded_num, encoded_text = rle_encode(text)

    # 3. 숫자 리스트로 나누기
    countlist = ''.join(map(str, encoded_num))
    textlist = ''.join(map(str, encoded_text))
 # 2. 텍스트를 숫자로 매핑
    # mapped_text = map_text_to_single_digit_numbers(''.join(encoded_text))
    mapped_text = map_text_to_single_digit_numbers(textlist)
    longnumber = countlist + mapped_text

    return longnumber


def rle_decode(encoded_num, encoded_text):
    """RLE 압축을 복원하는 함수"""
    decoded_data = []
    for count, char in zip(encoded_num, encoded_text):
        decoded_data.append(char * count)  # 문자와 반복 횟수를 기반으로 복원
    return ''.join(decoded_data)

def decrypt_rle_list(bignum_list):
    """암호화된 숫자 리스트를 복호화하는 함수"""
    # 1. 큰 숫자 리스트를 문자열로 합치기
    longnumber = ''.join(str(num) for num in bignum_list)
    
    # 2. 나눈 부분을 분리
    countlist = longnumber[:len(longnumber)//2]  # 처음 절반은 카운트 리스트
    textlist = longnumber[len(longnumber)//2:]  # 나머지는 텍스트 리스트
    
    # 3. 텍스트 리스트에서 숫자 부분 복호화
    encoded_num = [int(countlist[i:i+1]) for i in range(0, len(countlist))]
    mapped_text = map_numbers_to_text(textlist)
    
    # 4. RLE 복호화
    decoded_text = rle_decode(encoded_num, mapped_text)

    return decoded_text

def decrypt_base7(base10number):
    decoded_base7 = base10_to_base7(base10number)
    mapped_text = map_numbers_to_text(decoded_base7)
    return mapped_text

def add_lines(before_str, width):
    result = ''
    for i in range(0, len(before_str), width):
        result += before_str[i:i+width] + '\n'
    return result

def extract_value(text, key):
    if text is None:
        return False
    
    # key와 숫자 값을 찾는 정규식
    regex = r'{}:\s*(\S+)'.format(re.escape(key))
    
    match = re.search(regex, text)  # 정규식으로 매칭
    if match:
        return match.group(1)  # 찾은 값을 그대로 반환
    return False  # 값이 없으면 False 반환


def _compress(original_text, maxlen):
    sys.set_int_max_str_digits(maxlen)
    split_text = original_text.split(']')

    if len(split_text)>1:
        original_text = split_text[1]

    text = original_text.replace('\n', '')
    result = -1
    method = -1
    try:
        rlenum = make_rle_list(str(text))
    except:
        rlenum = text #오버플로우 에러 처리(아래의 코드 참고)

    if len(rlenum)< len(text) * 85 // 100: #압축률 59.83% +a
        method = 0
        print("optimise with rle")

        decimal_value = rlenum
        # 10진수 -> 127진법으로 변환
        base127_value = decimal_to_base127(int(decimal_value))
        result = base127_value
        # 출력
        print("Original number length:", len(text))
        print("base127 value length:", len(base127_value))
        
        #rle 썼다는 플래그 필요
    else: 
        method = 1
        print("optimise with base7: rate 59.83%") #압축률 59.83% 
        #rle 안썼다는 플래그 필요

        # # 텍스트를 숫자 문자열로 변환
        mapped_numbers = int(map_text_to_single_digit_numbers(text))
        # # 7진수 -> 10진수로 변환
        decimal_value = base7_to_base10(mapped_numbers) #압축률 15.5%

        # 10진수 -> 127진법으로 변환
        base127_value = decimal_to_base127(decimal_value) #압축률 52.43%
        result = base127_value
        # 출력
        print("Original number length:", len(str(original_text)))
        print("Compressed value length:", len(str(base127_value)))

    if len(split_text)>1:
        result = split_text[0]+" ]"+result

    return method,result
        #마지막 엔터는 안쳐야 함.

def _decompress(compressed_text,method_num, maxlen):
    sys.set_int_max_str_digits(maxlen)
    remove_header = compressed_text
    if compressed_text.startswith('[ width: '):
       index = compressed_text.find(']')
      
       remaining = compressed_text[index + 1:]  # 나머지 부분
       remove_header = remaining

    method = METHOD[method_num]

    decoded_base10 = decode_from_base127(remove_header)

    if method == "RLE":
        ascii_text = decrypt_rle_list(str(decoded_base10))
    
    elif method == "BASE7":
        ascii_text = decrypt_base7(decoded_base10)

    if compressed_text.startswith('[ width: '):
       index = compressed_text.find(']')
       first_part = compressed_text[:index]
       ascii_text = first_part + ' ]'+ascii_text

    return ascii_text


def rgb_to_saturation(r, g, b):
    r_scaled = r / 255.0
    g_scaled = g / 255.0
    b_scaled = b / 255.0

    # Convert RGB to HSV
    h, s, v = colorsys.rgb_to_hsv(r_scaled, g_scaled, b_scaled)

    return s



#------------API-----------------
app = FastAPI()

# CORS 설정
origins = [
    "https://compresspy.fly.dev",
    "https://iq6900.com",
  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용할 도메인
    allow_credentials=True,  # 쿠키 지원 여부
    allow_methods=["*"],  # 허용할 HTTP 메서드
    allow_headers=["*"],  # 허용할 헤더
)

class CompressData(BaseModel):
    ascii: str
    maxlen: int = 10000 

@app.post("/compress")
def compress(data: CompressData):
    original_text = data.ascii
    maxlen = data.maxlen

    method,result = _compress(original_text,maxlen)
    return {"message": "Compressed_str", "method":method, "result": result}

class DeCompressData(BaseModel):
    original_text: str
    method: int
    maxlen: int = 10000 

@app.post("/decompress")
def decompress(data: DeCompressData):
    
    original_text = data.original_text
    method = data.method
    maxlen = data.maxlen

    result = _decompress(original_text,method,maxlen)
   
    return {"message": "Decompressed ascii art", "result": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)
