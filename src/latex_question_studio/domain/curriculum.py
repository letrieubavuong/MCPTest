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
    if KHTN7_ROOT_ID in seen:
        values.update(subject='Khoa học tự nhiên',grade='7',chapter=values.get('chapter',''),lesson=values.get('lesson',''))
    if MATH7_ROOT_ID in seen:
        values.update(subject='Toán',grade='7',chapter=values.get('chapter',''),lesson=values.get('lesson',''))
    for root,subject in ((KHTN8_ROOT_ID,'Khoa học tự nhiên'),(MATH8_ROOT_ID,'Toán')):
        if root in seen:
            values.update(subject=subject,grade='8',chapter=values.get('chapter',''),lesson=values.get('lesson',''))
    for root,subject in ((KHTN9_ROOT_ID,'Khoa học tự nhiên'),(MATH9_ROOT_ID,'Toán')):
        if root in seen:
            values.update(subject=subject,grade='9',chapter=values.get('chapter',''),lesson=values.get('lesson',''))
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


KHTN7_ROOT_ID='curriculum:khtn7'
KHTN7_CHAPTERS=(
 ('Nguyên tử. Sơ lược về bảng tuần hoàn các nguyên tố hóa học',((2,'Nguyên tử'),(3,'Nguyên tố hóa học'),(4,'Sơ lược về bảng tuần hoàn các nguyên tố hóa học'))),
 ('Phân tử. Liên kết hóa học',((5,'Phân tử - Đơn chất - Hợp chất'),(6,'Giới thiệu về liên kết hóa học'),(7,'Hóa trị và công thức hóa học'))),
 ('Tốc độ',((8,'Tốc độ chuyển động'),(9,'Đo tốc độ'),(10,'Đồ thị quãng đường - thời gian'),(11,'Thảo luận về ảnh hưởng của tốc độ trong an toàn giao thông'))),
 ('Âm thanh',((12,'Sóng âm'),(13,'Độ to và độ cao của âm'),(14,'Phản xạ âm, chống ô nhiễm tiếng ồn'))),
 ('Ánh sáng',((15,'Năng lượng ánh sáng. Tia sáng, vùng tối'),(16,'Sự phản xạ ánh sáng'),(17,'Ảnh của vật qua gương phẳng'))),
 ('Từ',((18,'Nam châm'),(19,'Từ trường'),(20,'Chế tạo nam châm điện đơn giản'))),
 ('Trao đổi chất và chuyển hóa năng lượng ở sinh vật',((21,'Khái quát về trao đổi chất và chuyển hóa năng lượng'),(22,'Quang hợp ở thực vật'),(23,'Một số yếu tố ảnh hưởng đến quang hợp'),(24,'Thực hành: Chứng minh quang hợp ở cây xanh'),(25,'Hô hấp tế bào'),(26,'Một số yếu tố ảnh hưởng đến hô hấp tế bào'),(27,'Thực hành: Hô hấp ở thực vật'),(28,'Trao đổi khí ở sinh vật'),(29,'Vai trò của nước và chất dinh dưỡng đối với sinh vật'),(30,'Trao đổi nước và chất dinh dưỡng ở thực vật'),(31,'Trao đổi nước và chất dinh dưỡng ở động vật'),(32,'Thực hành: Chứng minh thân vận chuyển nước và lá thoát hơi nước'))),
 ('Cảm ứng ở sinh vật',((33,'Cảm ứng ở sinh vật và tập tính ở động vật'),(34,'Vận dụng hiện tượng cảm ứng ở sinh vật vào thực tiễn'),(35,'Thực hành: Cảm ứng ở sinh vật'))),
 ('Sinh trưởng và phát triển ở sinh vật',((36,'Khái quát về sinh trưởng và phát triển ở sinh vật'),(37,'Ứng dụng sinh trưởng và phát triển ở sinh vật vào thực tiễn'),(38,'Thực hành: Quan sát, mô tả sự sinh trưởng và phát triển ở một số sinh vật'))),
 ('Sinh sản ở sinh vật',((39,'Sinh sản vô tính ở sinh vật'),(40,'Sinh sản hữu tính ở sinh vật'),(41,'Một số yếu tố ảnh hưởng và điều hòa, điều khiển sinh sản ở sinh vật'),(42,'Cơ thể sinh vật là một thể thống nhất'))),
)


def khtn7_chapter_id(number):return KHTN7_ROOT_ID+f':chapter:{number:02}'
def khtn7_lesson_id(number):return KHTN7_ROOT_ID+f':lesson:{number:02}'


def khtn7_migration_sql():
    result=[(KHTN7_ROOT_ID,None,'subject','KHTN 7','KHTN7',None)]
    for number,(title,lessons) in enumerate(KHTN7_CHAPTERS,1):
        parent=khtn7_chapter_id(number)
        result.append((parent,KHTN7_ROOT_ID,'chapter',f'Chương {number}: {title}',f'KHTN7-C{number:02}',None))
        for index,name in lessons:
            result.append((khtn7_lesson_id(index),parent,'lesson',f'Bài {index}: {name}',f'KHTN7-C{number:02}-B{index:02}',None))
    def quote(value):return 'NULL' if value is None else "'"+str(value).replace("'","''")+"'"
    return tuple('INSERT OR IGNORE INTO taxonomy_nodes VALUES ('+','.join(quote(v) for v in row)+')' for row in result)


MATH7_ROOT_ID='curriculum:math7'
MATH7_CHAPTERS=(
 ('Số hữu tỉ',((1,'Tập hợp các số hữu tỉ'),(2,'Cộng, trừ, nhân, chia số hữu tỉ'),(3,'Lũy thừa với số mũ tự nhiên của một số hữu tỉ'),(4,'Thứ tự thực hiện các phép tính. Quy tắc chuyển vế'))),
 ('Số thực',((5,'Làm quen với số thập phân vô hạn tuần hoàn'),(6,'Số vô tỉ. Căn bậc hai số học'),(7,'Tập hợp các số thực'))),
 ('Góc và đường thẳng song song',((8,'Góc ở vị trí đặc biệt. Tia phân giác của một góc'),(9,'Hai đường thẳng song song và dấu hiệu nhận biết'),(10,'Tiên đề Euclid. Tính chất của hai đường thẳng song song'),(11,'Định lí và chứng minh định lí'))),
 ('Tam giác bằng nhau',((12,'Tổng các góc trong một tam giác'),(13,'Hai tam giác bằng nhau. Trường hợp bằng nhau thứ nhất của tam giác'),(14,'Trường hợp bằng nhau thứ hai và thứ ba của tam giác'),(15,'Các trường hợp bằng nhau của tam giác vuông'),(16,'Tam giác cân. Đường trung trực của đoạn thẳng'))),
 ('Thu thập và biểu diễn dữ liệu',((17,'Thu thập và phân loại dữ liệu'),(18,'Biểu đồ hình quạt tròn'),(19,'Biểu đồ đoạn thẳng'))),
 ('Tỉ lệ thức và đại lượng tỉ lệ',((20,'Tỉ lệ thức'),(21,'Tính chất của dãy tỉ số bằng nhau'),(22,'Đại lượng tỉ lệ thuận'),(23,'Đại lượng tỉ lệ nghịch'))),
 ('Biểu thức đại số và đa thức một biến',((24,'Biểu thức đại số'),(25,'Đa thức một biến'),(26,'Phép cộng và phép trừ đa thức một biến'),(27,'Phép nhân đa thức một biến'),(28,'Phép chia đa thức một biến'))),
 ('Làm quen với biến cố và xác suất của biến cố',((29,'Làm quen với biến cố'),(30,'Làm quen với xác suất của biến cố'))),
 ('Quan hệ giữa các yếu tố trong một tam giác',((31,'Quan hệ giữa góc và cạnh đối diện trong một tam giác'),(32,'Quan hệ giữa đường vuông góc và đường xiên'),(33,'Quan hệ giữa ba cạnh của một tam giác'),(34,'Sự đồng quy của ba đường trung tuyến, ba đường phân giác trong một tam giác'),(35,'Sự đồng quy của ba đường trung trực, ba đường cao trong một tam giác'))),
 ('Một số hình khối trong thực tiễn',((36,'Hình hộp chữ nhật và hình lập phương'),(37,'Hình lăng trụ đứng tam giác và hình lăng trụ đứng tứ giác'))),
)


def math7_chapter_id(number):return MATH7_ROOT_ID+f':chapter:{number:02}'
def math7_lesson_id(number):return MATH7_ROOT_ID+f':lesson:{number:02}'


def math7_migration_sql():
    result=[(MATH7_ROOT_ID,None,'subject','TOÁN 7','MATH7',None)]
    for number,(title,lessons) in enumerate(MATH7_CHAPTERS,1):
        parent=math7_chapter_id(number)
        result.append((parent,MATH7_ROOT_ID,'chapter',f'Chương {number}: {title}',f'MATH7-C{number:02}',None))
        for index,name in lessons:
            result.append((math7_lesson_id(index),parent,'lesson',f'Bài {index}: {name}',f'MATH7-C{number:02}-B{index:02}',None))
    def quote(value):return 'NULL' if value is None else "'"+str(value).replace("'","''")+"'"
    return tuple('INSERT OR IGNORE INTO taxonomy_nodes VALUES ('+','.join(quote(v) for v in row)+')' for row in result)


KHTN8_ROOT_ID='curriculum:khtn8'
MATH8_ROOT_ID='curriculum:math8'
KHTN8_INTRO='Sử dụng một số hóa chất, thiết bị cơ bản trong phòng thí nghiệm'
KHTN8_CHAPTERS=(
 ('Phản ứng hóa học',((2,'Phản ứng hóa học'),(3,'Mol và tỉ khối chất khí'),(4,'Dung dịch và nồng độ'),(5,'Định luật bảo toàn khối lượng và phương trình hóa học'),(6,'Tính theo phương trình hóa học'),(7,'Tốc độ phản ứng và chất xúc tác'))),
 ('Một số hợp chất thông dụng',((8,'Acid'),(9,'Base. Thang pH'),(10,'Oxide'),(11,'Muối'),(12,'Phân bón hóa học'))),
 ('Khối lượng riêng và áp suất',((13,'Khối lượng riêng'),(14,'Thực hành xác định khối lượng riêng'),(15,'Áp suất trên một bề mặt'),(16,'Áp suất chất lỏng. Áp suất khí quyển'),(17,'Lực đẩy Archimedes'))),
 ('Tác dụng làm quay của lực',((18,'Tác dụng làm quay của lực. Moment lực'),(19,'Đòn bẩy và ứng dụng'))),
 ('Điện',((20,'Hiện tượng nhiễm điện do cọ xát'),(21,'Dòng điện, nguồn điện'),(22,'Mạch điện đơn giản'),(23,'Tác dụng của dòng điện'),(24,'Cường độ dòng điện và hiệu điện thế'),(25,'Thực hành đo cường độ dòng điện và hiệu điện thế'))),
 ('Nhiệt',((26,'Năng lượng nhiệt và nội năng'),(27,'Thực hành đo năng lượng nhiệt bằng joulemeter'),(28,'Sự truyền nhiệt'),(29,'Sự nở vì nhiệt'))),
 ('Sinh học cơ thể người',((30,'Khái quát về cơ thể người'),(31,'Hệ vận động ở người'),(32,'Dinh dưỡng và tiêu hóa ở người'),(33,'Máu và hệ tuần hoàn của cơ thể người'),(34,'Hệ hô hấp ở người'),(35,'Hệ bài tiết ở người'),(36,'Điều hòa môi trường trong của cơ thể người'),(37,'Hệ thần kinh và các giác quan ở người'),(38,'Hệ nội tiết ở người'),(39,'Da và điều hòa thân nhiệt ở người'),(40,'Sinh sản ở người'))),
 ('Sinh vật và môi trường',((41,'Môi trường và các nhân tố sinh thái'),(42,'Quần thể sinh vật'),(43,'Quần xã sinh vật'),(44,'Hệ sinh thái'),(45,'Sinh quyển'),(46,'Cân bằng tự nhiên'))),
)
MATH8_CHAPTERS=(
 ('Đa thức',((1,'Đơn thức'),(2,'Đa thức'),(3,'Phép cộng và phép trừ đa thức'),(4,'Phép nhân đa thức'),(5,'Phép chia đa thức cho đơn thức'))),
 ('Hằng đẳng thức đáng nhớ và ứng dụng',((6,'Hiệu hai bình phương. Bình phương của một tổng hay một hiệu'),(7,'Lập phương của một tổng. Lập phương của một hiệu'),(8,'Tổng và hiệu hai lập phương'),(9,'Phân tích đa thức thành nhân tử'))),
 ('Tứ giác',((10,'Tứ giác'),(11,'Hình thang cân'),(12,'Hình bình hành'),(13,'Hình chữ nhật'),(14,'Hình thoi và hình vuông'))),
 ('Định lí Thalès',((15,'Định lí Thalès trong tam giác'),(16,'Đường trung bình của tam giác'),(17,'Tính chất đường phân giác của tam giác'))),
 ('Dữ liệu và biểu đồ',((18,'Thu thập và phân loại dữ liệu'),(19,'Biểu diễn dữ liệu bằng bảng, biểu đồ'),(20,'Phân tích số liệu thống kê dựa vào biểu đồ'))),
 ('Phân thức đại số',((21,'Phân thức đại số'),(22,'Tính chất cơ bản của phân thức đại số'),(23,'Phép cộng và phép trừ phân thức đại số'),(24,'Phép nhân và phép chia phân thức đại số'))),
 ('Phương trình bậc nhất và hàm số bậc nhất',((25,'Phương trình bậc nhất một ẩn'),(26,'Giải bài toán bằng cách lập phương trình'),(27,'Khái niệm hàm số và đồ thị của hàm số'),(28,'Hàm số bậc nhất và đồ thị của hàm số bậc nhất'),(29,'Hệ số góc của đường thẳng'))),
 ('Mở đầu về tính xác suất của biến cố',((30,'Kết quả có thể và kết quả thuận lợi'),(31,'Cách tính xác suất của biến cố bằng tỉ số'),(32,'Mối liên hệ giữa xác suất thực nghiệm với xác suất và ứng dụng'))),
 ('Tam giác đồng dạng',((33,'Hai tam giác đồng dạng'),(34,'Ba trường hợp đồng dạng của hai tam giác'),(35,'Định lí Pythagore và ứng dụng'),(36,'Các trường hợp đồng dạng của hai tam giác vuông'),(37,'Hình đồng dạng'))),
 ('Một số hình khối trong thực tiễn',((38,'Hình chóp tam giác đều'),(39,'Hình chóp tứ giác đều'))),
)


def grade8_migration_sql():
    result=[]
    for root,label,code,chapters in ((KHTN8_ROOT_ID,'KHTN 8','KHTN8',KHTN8_CHAPTERS),(MATH8_ROOT_ID,'TOÁN 8','MATH8',MATH8_CHAPTERS)):
        result.append((root,None,'subject',label,code,None))
        if root==KHTN8_ROOT_ID:
            result.append((root+':lesson:01',root,'lesson','Bài 1: '+KHTN8_INTRO,code+'-C00-B01',None))
        for number,(title,lessons) in enumerate(chapters,1):
            parent=root+f':chapter:{number:02}'
            result.append((parent,root,'chapter',f'Chương {number}: {title}',code+f'-C{number:02}',None))
            for index,name in lessons:
                result.append((root+f':lesson:{index:02}',parent,'lesson',f'Bài {index}: {name}',code+f'-C{number:02}-B{index:02}',None))
    def quote(value):return 'NULL' if value is None else "'"+str(value).replace("'","''")+"'"
    return tuple('INSERT OR IGNORE INTO taxonomy_nodes VALUES ('+','.join(quote(v) for v in row)+')' for row in result)


KHTN9_ROOT_ID='curriculum:khtn9'
MATH9_ROOT_ID='curriculum:math9'
KHTN9_INTRO='Nhận biết một số dụng cụ, hoá chất. Thuyết trình một vấn đề khoa học'
KHTN9_CHAPTERS=(
 ('Năng lượng cơ học',((2,'Động năng. Thế năng'),(3,'Cơ năng'),(4,'Công và công suất'))),
 ('Ánh sáng',((5,'Khúc xạ ánh sáng'),(6,'Phản xạ toàn phần'),(7,'Lăng kính'),(8,'Thấu kính'),(9,'Thực hành đo tiêu cự của thấu kính hội tụ'),(10,'Kính lúp. Bài tập thấu kính'))),
 ('Điện',((11,'Điện trở. Định luật Ohm'),(12,'Đoạn mạch nối tiếp, song song'),(13,'Năng lượng của dòng điện và công suất điện'))),
 ('Điện từ',((14,'Cảm ứng điện từ. Nguyên tắc tạo ra dòng điện xoay chiều'),(15,'Tác dụng của dòng điện xoay chiều'))),
 ('Năng lượng với cuộc sống',((16,'Vòng năng lượng trên Trái Đất. Năng lượng hoá thạch'),(17,'Một số dạng năng lượng tái tạo'))),
 ('Kim loại. Sự khác nhau cơ bản giữa phi kim và kim loại',((18,'Tính chất chung của kim loại'),(19,'Dãy hoạt động hoá học'),(20,'Tách kim loại và việc sử dụng hợp kim'),(21,'Sự khác nhau cơ bản giữa phi kim và kim loại'))),
 ('Giới thiệu về chất hữu cơ. Hydrocarbon và nguồn nhiên liệu',((22,'Giới thiệu về hợp chất hữu cơ'),(23,'Alkane'),(24,'Alkene'),(25,'Nguồn nhiên liệu'))),
 ('Ethylic alcohol và Acetic acid',((26,'Ethylic alcohol'),(27,'Acetic acid'))),
 ('Lipid. Carbohydrate. Protein. Polymer',((28,'Lipid'),(29,'Carbohydrate. Glucose và saccharose'),(30,'Tinh bột và cellulose'),(31,'Protein'),(32,'Polymer'))),
 ('Khai thác tài nguyên từ vỏ trái đất',((33,'Sơ lược về hoá học vỏ Trái Đất và khai thác tài nguyên từ vỏ Trái Đất'),(34,'Khai thác đá vôi. Công nghiệp silicate'),(35,'Khai thác nhiên liệu hoá thạch. Nguồn carbon. Chu trình carbon và sự ấm lên toàn cầu'))),
 ('Di truyền học Mendel. Cơ sở phân tử của hiện tượng di truyền',((36,'Khái quát về di truyền học'),(37,'Các quy luật di truyền của Mendel'),(38,'Nucleic acid và gene'),(39,'Tái bản DNA và phiên mã tạo RNA'),(40,'Dịch mã và mối quan hệ từ gene đến tính trạng'),(41,'Đột biến gene'))),
 ('Di truyền nhiễm sắc thể',((42,'Nhiễm sắc thể và bộ nhiễm sắc thể'),(43,'Nguyên phân và giảm phân'),(44,'Nhiễm sắc thể giới tính và cơ chế xác định giới tính'),(45,'Di truyền liên kết'),(46,'Đột biến nhiễm sắc thể'))),
 ('Di truyền học với con người và đời sống',((47,'Di truyền học với con người'),(48,'Ứng dụng công nghệ di truyền vào đời sống'))),
 ('Tiến hóa',((49,'Khái niệm tiến hoá và các hình thức chọn lọc'),(50,'Cơ chế tiến hoá'),(51,'Sự phát sinh và phát triển sự sống trên Trái Đất'))),
)
MATH9_CHAPTERS=(
 ('Phương trình và hệ hai phương trình bậc nhất hai ẩn',((1,'Khái niệm phương trình và hệ hai phương trình bậc nhất hai ẩn'),(2,'Giải hệ hai phương trình bậc nhất hai ẩn'),(3,'Giải bài toán bằng cách lập hệ phương trình'))),
 ('Phương trình và bất phương trình bậc nhất một ẩn',((4,'Phương trình quy về phương trình bậc nhất một ẩn'),(5,'Bất đẳng thức và tính chất'),(6,'Bất phương trình bậc nhất một ẩn'))),
 ('Căn bậc hai và căn bậc ba',((7,'Căn bậc hai và căn thức bậc hai'),(8,'Khai căn bậc hai với phép nhân và phép chia'),(9,'Biến đổi đơn giản và rút gọn biểu thức chứa căn thức bậc hai'),(10,'Căn bậc ba và căn thức bậc ba'))),
 ('Hệ thức lượng trong tam giác vuông',((11,'Tỉ số lượng giác của góc nhọn'),(12,'Một số hệ thức giữa cạnh, góc trong tam giác vuông và ứng dụng'))),
 ('Đường tròn',((13,'Mở đầu về đường tròn'),(14,'Cung và dây của một đường tròn'),(15,'Độ dài của cung tròn. Diện tích hình quạt tròn và hình vành khuyên'),(16,'Vị trí tương đối của đường thẳng và đường tròn'),(17,'Vị trí tương đối của hai đường tròn'))),
 ('Hàm số y = ax² (a ≠ 0). Phương trình bậc hai một ẩn',((18,'Hàm số y = ax² (a ≠ 0)'),(19,'Phương trình bậc hai một ẩn'),(20,'Định lí Viète và ứng dụng'),(21,'Giải bài toán bằng cách lập phương trình'))),
 ('Tần số và tần số tương đối',((22,'Bảng tần số và biểu đồ tần số'),(23,'Bảng tần số tương đối và biểu đồ tần số tương đối'),(24,'Bảng tần số, tần số tương đối ghép nhóm và biểu đồ'))),
 ('Xác suất của biến cố trong một số mô hình xác suất đơn giản',((25,'Phép thử ngẫu nhiên và không gian mẫu'),(26,'Xác suất của biến cố liên quan tới phép thử'))),
 ('Đường tròn ngoại tiếp và đường tròn nội tiếp',((27,'Góc nội tiếp'),(28,'Đường tròn ngoại tiếp và đường tròn nội tiếp của một tam giác'),(29,'Tứ giác nội tiếp'),(30,'Đa giác đều'))),
 ('Một số hình khối trong thực tiễn',((31,'Hình trụ và hình nón'),(32,'Hình cầu'))),
)


def grade9_migration_sql():
    result=[]
    for root,label,code,chapters in ((KHTN9_ROOT_ID,'KHTN 9','KHTN9',KHTN9_CHAPTERS),(MATH9_ROOT_ID,'TOÁN 9','MATH9',MATH9_CHAPTERS)):
        result.append((root,None,'subject',label,code,None))
        if root==KHTN9_ROOT_ID:
            result.append((root+':lesson:01',root,'lesson','Bài 1: '+KHTN9_INTRO,code+'-C00-B01',None))
        for number,(title,lessons) in enumerate(chapters,1):
            parent=root+f':chapter:{number:02}'
            result.append((parent,root,'chapter',f'Chương {number}: {title}',code+f'-C{number:02}',None))
            for index,name in lessons:
                result.append((root+f':lesson:{index:02}',parent,'lesson',f'Bài {index}: {name}',code+f'-C{number:02}-B{index:02}',None))
    def quote(value):return 'NULL' if value is None else "'"+str(value).replace("'","''")+"'"
    return tuple('INSERT OR IGNORE INTO taxonomy_nodes VALUES ('+','.join(quote(v) for v in row)+')' for row in result)
