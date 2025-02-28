from openpyxl import load_workbook

def parse_relatorio_excel(file_path):
    
    wb = load_workbook(file_path, data_only=True)
    sheet = wb.active
    
    data_blocks = []      
    current_block = []    
    current_columns = []  
    
    STATE_SEARCHING_HEADER = 0
    STATE_READING_DATA     = 1
    STATE_SEARCHING_NEXT   = 2
    
    state = STATE_SEARCHING_HEADER
    lines_without_header = 0  
    
    for row in sheet.iter_rows(values_only=True):
        
        first_cell = row[0] if row else None
        
        if isinstance(first_cell, str):
            first_cell = first_cell.strip().lower()
        
        if not first_cell:
            first_cell = None
        
        
        if state == STATE_SEARCHING_HEADER:
            if first_cell == 'data':
                current_columns = [str(x).strip().lower() if x else None for x in row]
                current_block = []
                state = STATE_READING_DATA
            else:
                pass  
        
        elif state == STATE_READING_DATA:
            if first_cell is None:
                if current_block:
                    data_blocks.append(current_block)
                
                current_block = []
                current_columns = []
                state = STATE_SEARCHING_NEXT
                lines_without_header = 0
            else:

                row_dict = {}
                for col_index, col_name in enumerate(current_columns):
                    if col_name:  
                        row_dict[col_name] = row[col_index] if col_index < len(row) else None
                current_block.append(row_dict)
        
        elif state == STATE_SEARCHING_NEXT:
            if first_cell == 'data':
                current_columns = [str(x).strip().lower() if x else None for x in row]
                current_block = []
                state = STATE_READING_DATA
            else:
                lines_without_header += 1
                if lines_without_header >= 6:
                    break
        
    if state == STATE_READING_DATA and current_block:
        data_blocks.append(current_block)
    
    return data_blocks

if __name__ == "__main__":
    file_path = "Fatura-Excel-fev.xlsx"
    blocks = parse_relatorio_excel(file_path)
    
    print(f"Foram encontrados {len(blocks)} bloco(s) de dados.")
    for i, block in enumerate(blocks, start=1):
        print(f"\n--- Bloco {i} ---")
        for row_data in block[:5]:  
            print(row_data)
