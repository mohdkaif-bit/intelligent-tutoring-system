# run this once
import pickle

pkl_path = r"C:\Users\mkaif\Desktop\intelligent-tutoring-system\backend\.storage\vectorstores\default_user\Document1.pdf_2d221e8cd111\faiss\index.pkl"

with open(pkl_path, "rb") as f:
    data = pickle.load(f)

docstore, index_to_docstore_id = data

for uuid, doc in docstore._dict.items():
    print(f"UUID     : {uuid}")
    print(f"Metadata : {doc.metadata}")
    print(f"Text     : {doc.page_content[:80]}")
    print("-" * 50)