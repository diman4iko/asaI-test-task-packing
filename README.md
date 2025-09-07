# АСАИ – Тестовое задание – Упаковка


## Установка
1. Клонируйте репозиторий

2. docker-compose up -d


## Видео демонстрация
Ссылка на видео: https://youtu.be/eiMwhPFftGE


## Что реализовано
1. Подгрузка csv файла производственного задания
2. Поле где оператор может записать свои данные
3. Можно отправить детали в брак с указанием причины брака
4. Транспортная этикетка формируется после упаковки
5. После упаковки заказ отмечается упакованным

## Структура проекта
models/packaging_defective_wizard.py - Для пометки товара как брак

models/packaging_oder_detectie_wizar.py - Для пометки, что заказ не может быть выполнен

models/packaging_item - модель товара

models/packaging_labeж - модель для транспортных этикеток

models/packaging_order.py - модель заказа

views/packaging_item_views.xml - вью для каждого товара

views/packaging_label_views.xml - вью для транспортной этикетки

views/packaging_order_create_views.xml - вью для содания заказа

views/packaging_order_form_views.xml - вью для товаров в заказе

views/packaging_order_views.xml - основная вьюшка

security/ir.model.access.csv - права доступа


