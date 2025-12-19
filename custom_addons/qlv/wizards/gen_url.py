import base64

graph = """
graph LR
    Customer["Khách hàng"] -- "Đưa Vàng cũ (Vàng Tây)" --> InputData["Input: Original Product"]
    InputData -- "Tính toán (Purity 60%)" --> ConversionLogic["Logic Quy đổi (Mixin)"]
    ConversionLogic -- "Kết quả" --> TargetData["Target: Vàng 9999\\nQty: 0.6 chỉ"]
    TargetData -- "Tạo dòng" --> StockMove["Stock Move (Phiếu Nhập)"]
    subgraph MoveDetails [Dữ liệu trên Stock Move]
        MainProd["Product Idea: Vàng 9999"]
        MainQty["Quantity: 0.6"]
        MetaOrigin["Info: Vàng Tây (Gốc)"]
        MetaWeight["Info: 1.0 (TL Gốc)"]
    end
    StockMove -.-> MainProd
    StockMove -- "Tăng Tồn kho" --> Warehouse["Kho: Vàng 9999"]
"""

# Mermaid.ink expects standard base64 encoding of the code string
encoded = base64.urlsafe_b64encode(graph.encode('utf-8')).decode('utf-8')
print(f"https://mermaid.ink/img/{encoded}")
