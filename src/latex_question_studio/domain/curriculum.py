"""KHTN 6 curriculum supplied by the user; numbering is part of its identity."""
ROOT_ID='curriculum:khtn6'
CHAPTERS=(
 ('Mở đầu về Khoa học tự nhiên',(
  (1,'Giới thiệu về Khoa học tự nhiên'),(2,'An toàn trong phòng thực hành'),
  (3,'Sử dụng kính lúp'),(4,'Sử dụng kính hiển vi quang học'),
  (5,'Đo chiều dài'),(6,'Đo khối lượng'),(7,'Đo thời gian'),(8,'Đo nhiệt độ'))),
 ('Chất quanh ta',((9,'Sự đa dạng của chất'),(10,'Các thể của chất và sự chuyển thể'),(11,'Oxygen. Không khí'))),
 ('Một số vật liệu, nguyên liệu, nhiên liệu, lương thực - thực phẩm thông dụng',(
  (12,'Một số vật liệu'),(13,'Một số nguyên liệu'),(14,'Một số nhiên liệu'),(15,'Một số lương thực, thực phẩm'))),
 ('Hỗn hợp. Tách chất ra khỏi hỗn hợp',((16,'Hỗn hợp các chất'),(17,'Tách chất khỏi hỗn hợp'))),
 ('Tế bào',((18,'Tế bào – Đơn vị cơ bản của sự sống'),
  (19,'Cấu tạo và chức năng các thành phần của tế bào'),(20,'Sự lớn lên và sinh sản của tế bào'),
  (21,'Thực hành: Quan sát và phân biệt một số loại tế bào'))),
 ('Từ tế bào đến cơ thể',((22,'Cơ thể sinh vật'),(23,'Tổ chức cơ thể đa bào'),
  (24,'Thực hành: Quan sát và mô tả cơ thể đơn bào, cơ thể đa bào'))),
 ('Đa dạng thế giới sống',((25,'Hệ thống phân loại sinh vật'),(26,'Khóa lưỡng phân'),
  (27,'Vi khuẩn'),(28,'Thực hành: Làm sữa chua và quan sát vi khuẩn'),(29,'Virus'),
  (30,'Nguyên sinh vật'),(31,'Thực hành: Quan sát nguyên sinh vật'),(32,'Nấm'),
  (33,'Thực hành: Quan sát các loại nấm'),(34,'Thực vật'),
  (35,'Thực hành: Quan sát và phân biệt một số nhóm thực vật'),(36,'Động vật'),
  (37,'Thực hành: Quan sát và nhận biết một số nhóm động vật ngoài thiên nhiên'),
  (38,'Đa dạng sinh học'),(39,'Tìm hiểu sinh vật ngoài thiên nhiên'))),
 ('Lực trong đời sống',((40,'Lực là gì?'),(41,'Biểu diễn lực'),(42,'Biến dạng của lò xo'),
  (43,'Trọng lực, lực hấp dẫn'),(44,'Lực ma sát'),(45,'Lực cản của nước'))),
 ('Năng lượng',((46,'Năng lượng và sự truyền năng lượng'),(47,'Một số dạng năng lượng'),
  (48,'Sự chuyển hóa năng lượng'),(49,'Năng lượng hao phí'),(50,'Năng lượng tái tạo'),(51,'Tiết kiệm năng lượng'))),
 ('Trái đất và bầu trời',((52,'Chuyển động nhìn thấy của Mặt Trời. Thiên thể'),
  (53,'Mặt Trăng'),(54,'Hệ Mặt Trời'),(55,'Ngân hà'))),
)


def chapter_id(number):return ROOT_ID+f':chapter:{number:02}'
def lesson_id(number):return ROOT_ID+f':lesson:{number:02}'


def rows():
    result=[(ROOT_ID,None,'subject','KHTN 6','KHTN6',None)]
    for number,(title,lessons) in enumerate(CHAPTERS,1):
        parent=chapter_id(number)
        result.append((parent,ROOT_ID,'chapter',f'Chương {number}: {title}',f'KHTN6-C{number:02}',None))
        for index,name in lessons:
            result.append((lesson_id(index),parent,'lesson',f'Bài {index}: {name}',f'KHTN6-C{number:02}-B{index:02}',None))
    return result


def migration_sql():
    def quote(value):return 'NULL' if value is None else "'"+str(value).replace("'","''")+"'"
    return tuple('INSERT OR IGNORE INTO taxonomy_nodes VALUES ('+','.join(quote(v) for v in row)+')' for row in rows())


def classification(nodes, selected_id):
    lookup={n['id']:n for n in nodes};chain=[];seen=set()
    while selected_id in lookup and selected_id not in seen:
        seen.add(selected_id);node=lookup[selected_id];chain.append(node);selected_id=node['parent_id']
    values={n['kind']:n['name'] for n in reversed(chain) if n['kind'] in ('subject','grade','chapter','lesson','topic')}
    if ROOT_ID in seen:
        values.update(subject='Khoa học tự nhiên',grade='6',chapter=values.get('chapter',''),lesson=values.get('lesson',''))
    if MATH_ROOT_ID in seen:
        values.update(subject='Toán',grade='6',chapter=values.get('chapter',''),lesson=values.get('lesson',''))
    return values


def breadcrumb(nodes, selected_id):
    lookup={n['id']:n for n in nodes};parts=[];seen=set()
    while selected_id in lookup and selected_id not in seen:
        seen.add(selected_id);node=lookup[selected_id]
        parts.append(node['name'] if not parts else node['name'].split(':',1)[0])
        selected_id=node['parent_id']
    return ' › '.join(reversed(parts))

MATH_ROOT_ID='curriculum:math6'
MATH_CHAPTERS=(
 ('Tập hợp các số tự nhiên',((1,'Tập hợp'),(2,'Cách ghi số tự nhiên'),(3,'Thứ tự trong tập hợp các số tự nhiên'),(4,'Phép cộng và phép trừ số tự nhiên'),(5,'Phép nhân và phép chia số tự nhiên'),(6,'Lũy thừa với số mũ tự nhiên'),(7,'Thứ tự thực hiện các phép tính'))),
 ('Tính chia hết trong tập hợp các số tự nhiên',((8,'Quan hệ chia hết và tính chất'),(9,'Dấu hiệu chia hết'),(10,'Số nguyên tố'),(11,'Ước chung. Ước chung lớn nhất'),(12,'Bội chung. Bội chung nhỏ nhất'))),
 ('Số nguyên',((13,'Tập hợp các số nguyên'),(14,'Phép cộng và phép trừ số nguyên'),(15,'Quy tắc dấu ngoặc'),(16,'Phép nhân số nguyên'),(17,'Phép chia hết. Ước và bội của một số nguyên'))),
 ('Một số hình phẳng trong thực tiễn',((18,'Hình tam giác đều. hình vuông. hình lục giác đều'),(19,'hình chữ nhật. Hình thoi hình bình hành. Hình thang cân'),(20,'Chu vi và diện tích của một số tứ giác đã học'))),
 ('Tính đối xứng của hình phẳng trong tự nhiên',((21,'Hình có trục đối xứng'),(22,'Hình có tâm đối xứng'))),
 ('Phân số',((23,'Mở rộng phân số. Phân số bằng nhau'),(24,'So sánh phân số. Hỗn số dương'),('practice13','Luyện tập chung trang 13'),(25,'Phép cộng và phép trừ phân số'),(26,'Phép nhân và phép chia phân số'),(27,'Hai bài toán về phân số'))),
 ('Số thập phân',((28,'Số thập phân'),(29,'Tính toán với số thập phân'),(30,'Làm tròn và ước lượng'),(31,'Một số bài toán về tỉ số và tỉ số phần trăm'))),
 ('Những hình học cơ bản',((32,'Điểm và đường thẳng'),(33,'Điểm nằm giữa hai điểm. Tia'),(34,'Đoạn thẳng. Độ dài đoạn thẳng'),(35,'Trung điểm của đoạn thẳng'),('practice57','Luyện tập chung trang 57'),(36,'Góc'),(37,'Số đo góc'))),
 ('Dữ liệu và xác suất thực nghiệm',((38,'Dữ liệu và thu thập dữ liệu'),(39,'Bảng thống kê và biểu đồ tranh'),(40,'Biểu đồ cột'),(41,'Biểu đồ cột kép'),(42,'Kết quả có thể và sự kiện trong trò chơi, thí nghiệm'),(43,'Xác suất thực nghiệm'))),
)


def math_chapter_id(number):return MATH_ROOT_ID+f':chapter:{number:02}'
def math_lesson_id(number):return MATH_ROOT_ID+f':lesson:{number:02}'


def math_rows():
    result=[(MATH_ROOT_ID,None,'subject','TOÁN 6','MATH6',None)]
    for number,(title,lessons) in enumerate(MATH_CHAPTERS,1):
        parent=math_chapter_id(number)
        result.append((parent,MATH_ROOT_ID,'chapter',f'Chương {number}: {title}',f'MATH6-C{number:02}',None))
        for position,(index,name) in enumerate(lessons,1):
            node_id=math_lesson_id(index) if isinstance(index,int) else MATH_ROOT_ID+':'+index
            label=f'Bài {index}: {name}' if isinstance(index,int) else name
            result.append((node_id,parent,'lesson',label,f'MATH6-C{number:02}-P{position:02}',None))
    return result


def math_migration_sql():
    def quote(value):return 'NULL' if value is None else "'"+str(value).replace("'","''")+"'"
    return tuple('INSERT OR IGNORE INTO taxonomy_nodes VALUES ('+','.join(quote(v) for v in row)+')' for row in math_rows())
