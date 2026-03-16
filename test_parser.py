from parser import parse_document

file_path = "sample_contract.pdf" 

text = parse_document(file_path)

print("Extracted text preview:")
print(text[:500])
