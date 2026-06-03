import streamlit as st
import psycopg2
import math

DB_URL = "postgresql://admin:adminpassword@db:5432/isodb"

CONTAINER_LENGTHS = ["10 фт", "20 фт", "40 фт", "45 фт"]

CONTAINER_DATASET_RULES = [
    ("контейнер", CONTAINER_LENGTHS, "8.6 фт", "стандартный", ["генеральный"]),
    ("high-cube контейнер", CONTAINER_LENGTHS, "9.6 фт", "стандартный", ["генеральный"]),
    ("open-top контейнер", CONTAINER_LENGTHS, "8.6 фт", "сверху", ["негабаритный", "генеральный"]),
    ("open-side контейнер", CONTAINER_LENGTHS, "8.6 фт", "сбоку", ["генеральный"]),
    ("high-cube open-top контейнер", CONTAINER_LENGTHS, "9.6 фт", "сверху", ["негабаритный", "генеральный"]),
    ("high-cube open-side контейнер", CONTAINER_LENGTHS, "9.6 фт", "сбоку", ["генеральный"]),
    ("танк-контейнер", CONTAINER_LENGTHS, "8.6 фт", "стандартный", ["жидкий", "газообразный"]),
    ("high-cube танк-контейнер", CONTAINER_LENGTHS, "9.6 фт", "стандартный", ["жидкий", "газообразный"]),
    ("платформа", ["20 фт", "40 фт", "45 фт"], "неизмеримо", "сверху", ["негабаритный"]),
    ("реф-контейнер", CONTAINER_LENGTHS, "8.6 фт", "стандартный", ["требующий постоянной температуры"]),
    ("high-cube реф-контейнер", CONTAINER_LENGTHS, "9.6 фт", "стандартный", ["требующий постоянной температуры"]),
    ("контейнер с вентиляцией", CONTAINER_LENGTHS, "8.6 фт", "стандартный", ["требующий вентиляции"]),
    ("high-cube контейнер с вентиляцией", CONTAINER_LENGTHS, "9.6 фт", "стандартный", ["требующий вентиляции"]),
    ("балк-контейнер", CONTAINER_LENGTHS, "8.6 фт", "сверху", ["насыпной"]),
]

def get_db_connection():
    return psycopg2.connect(DB_URL)

def get_properties():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, data_type FROM properties ORDER BY id;")
            return cur.fetchall()

def update_property_name(prop_id, new_name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE properties SET name = %s WHERE id = %s;", (new_name, prop_id))
            conn.commit()

def update_property_type(prop_id, new_type):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE properties SET data_type = %s WHERE id = %s;",
                (new_type, prop_id)
            )
            conn.commit()

def get_options(prop_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, option_value FROM property_options WHERE property_id = %s ORDER BY id;", (prop_id,))
            return cur.fetchall()

def add_option(prop_id, value):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Проверяем, есть ли уже такое значение
            cur.execute("SELECT id FROM property_options WHERE property_id = %s AND option_value = %s;", (prop_id, value))
            if cur.fetchone():
                return False # Дубликат найден
            cur.execute("INSERT INTO property_options (property_id, option_value) VALUES (%s, %s);", (prop_id, value))
            conn.commit()
            return True

def update_option(opt_id, prop_id, old_value, new_value):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM property_options WHERE property_id = %s AND option_value = %s;", (prop_id, new_value))
            if cur.fetchone():
                return False # Нельзя переименовать в уже существующее
            # Меняем в справочнике
            cur.execute("UPDATE property_options SET option_value = %s WHERE id = %s;", (new_value, opt_id))
            # Каскадно меняем у всех контейнеров, чтобы не потерять данные
            cur.execute("UPDATE container_values SET value = %s WHERE property_id = %s AND value = %s;", (new_value, prop_id, old_value))
            conn.commit()
            return True

def delete_option(opt_id, prop_id, value):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Удаляем строго по уникальному ID строки
            cur.execute("DELETE FROM property_options WHERE id = %s;", (opt_id,))
            cur.execute("DELETE FROM container_values WHERE property_id = %s AND value = %s;", (prop_id, value))
            conn.commit()

def get_containers():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM containers ORDER BY id;")
            return cur.fetchall()
        
def get_container_properties(container_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.name
                FROM container_values cv
                JOIN properties p ON p.id = cv.property_id
                WHERE cv.container_id = %s
                GROUP BY p.id, p.name
                ORDER BY p.id;
            """, (container_id,))
            return cur.fetchall()
        
def get_null_properties():

    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    c.name,
                    p.name
                FROM container_values cv
                JOIN containers c
                    ON c.id = cv.container_id
                JOIN properties p
                    ON p.id = cv.property_id
                WHERE cv.value IS NULL
                ORDER BY p.name, c.name;
            """)

            return cur.fetchall()
        
def get_container_property_values(container_id, property_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT value
                FROM container_values
                WHERE container_id = %s
                AND property_id = %s
                AND value IS NOT NULL;
            """, (container_id, property_id))

            return [row[0] for row in cur.fetchall()]

def add_property_to_container(container_id, property_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT id
                FROM container_values
                WHERE container_id = %s
                AND property_id = %s
                LIMIT 1;
            """, (container_id, property_id))

            if cur.fetchone():
                return False

            cur.execute("""
                INSERT INTO container_values (
                    container_id,
                    property_id,
                    value
                )
                VALUES (%s, %s, NULL);
            """, (container_id, property_id))

            conn.commit()

            return True
        
def set_container_property_value(container_id, property_id, value):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT id
                FROM container_values
                WHERE container_id = %s
                AND property_id = %s
                AND value IS NULL
                LIMIT 1;
            """, (container_id, property_id))

            null_row = cur.fetchone()

            if null_row:

                cur.execute("""
                    UPDATE container_values
                    SET value = %s
                    WHERE id = %s;
                """, (value, null_row[0]))

            else:

                cur.execute("""
                    INSERT INTO container_values (
                        container_id,
                        property_id,
                        value
                    )
                    VALUES (%s, %s, %s);
                """, (container_id, property_id, value))

            conn.commit()

def remove_property_from_container(container_id, property_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                DELETE FROM container_values
                WHERE container_id = %s
                AND property_id = %s;
            """, (container_id, property_id))

            conn.commit()

def delete_container_property_values(container_id, property_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                DELETE FROM container_values
                WHERE container_id = %s
                AND property_id = %s;
            """, (container_id, property_id))

            conn.commit()

def add_container(name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "SELECT id FROM containers WHERE name = %s;",
                (name,)
            )

            if cur.fetchone():
                return False

            cur.execute(
                "INSERT INTO containers (name) VALUES (%s) RETURNING id;",
                (name,)
            )

            container_id = cur.fetchone()[0]

            cur.execute(
                "SELECT id FROM properties;"
            )

            properties = cur.fetchall()

            for prop in properties:
                cur.execute(
                    """
                    INSERT INTO container_values (container_id, property_id, value)
                    VALUES (%s, %s, NULL);
                    """,
                    (container_id, prop[0])
                )

            conn.commit()

            return True

def update_container(cont_id, new_name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM containers WHERE name = %s;", (new_name,))
            if cur.fetchone():
                return False
            cur.execute("UPDATE containers SET name = %s WHERE id = %s;", (new_name, cont_id))
            conn.commit()
            return True

def delete_container(cont_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # ON DELETE CASCADE в БД автоматически удалит связанные значения из container_values
            cur.execute("DELETE FROM containers WHERE id = %s;", (cont_id,))
            conn.commit()

def add_property(name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM properties WHERE name = %s;", (name,))
            if cur.fetchone():
                return False
            # По умолчанию задаем тип ENUM, как договаривались ранее
            cur.execute("INSERT INTO properties (name, data_type) VALUES (%s, 'ENUM');", (name,))
            conn.commit()
            return True

def delete_property(prop_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # ON DELETE CASCADE автоматически удалит все "Возможные значения" для этого свойства
            # и все присвоенные значения у контейнеров
            cur.execute("DELETE FROM properties WHERE id = %s;", (prop_id,))
            conn.commit()

def get_property_by_id(property_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT id, name, data_type
                FROM properties
                WHERE id = %s;
            """, (property_id,))

            return cur.fetchone()
        
def property_has_non_numeric_values(property_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT value
                FROM container_values
                WHERE property_id = %s
                AND value IS NOT NULL;
            """, (property_id,))

            values = cur.fetchall()

            for value in values:

                try:
                    parts = value[0].split(";")

                    if len(parts) != 2:
                        return True

                    float(parts[0])
                    float(parts[1])
                except:
                    return True

            return False

def normalize_model_text(value):
    return str(value).strip().lower().replace("ё", "е")

def make_model_feature(property_name, value):
    return f"{normalize_model_text(property_name)}={normalize_model_text(value)}"

def normalize_container_name(name):
    return normalize_model_text(name).replace("стандартный контейнер", "контейнер")

def build_container_training_samples():
    samples = []

    for (
        container_type,
        lengths,
        height,
        loading_type,
        cargo_types
    ) in CONTAINER_DATASET_RULES:
        for length in lengths:
            container_name = f"{length} {container_type}"

            for cargo_type in cargo_types:
                samples.append(
                    (
                        container_name,
                        {
                            "длина": length,
                            "высота": height,
                            "вид погрузки": loading_type,
                            "тип перевозимого груза": cargo_type
                        }
                    )
                )

    return samples

@st.cache_resource
def train_container_classifier():
    samples = build_container_training_samples()
    labels = sorted({label for label, _ in samples})
    label_index = {label: index for index, label in enumerate(labels)}

    feature_names = {"__bias__"}
    encoded_samples = []

    for label, feature_values in samples:
        features = {"__bias__"}

        for property_name, value in feature_values.items():
            features.add(make_model_feature(property_name, value))

        encoded_samples.append((label_index[label], features))
        feature_names.update(features)

    feature_names = sorted(feature_names)
    feature_index = {
        feature_name: index
        for index, feature_name in enumerate(feature_names)
    }

    class_count = len(labels)
    feature_count = len(feature_names)
    weights = [
        [0.0 for _ in range(feature_count)]
        for _ in range(class_count)
    ]

    learning_rate = 0.18
    epochs = 450

    for _ in range(epochs):
        for target_index, features in encoded_samples:
            active_feature_indexes = [
                feature_index[feature]
                for feature in features
            ]
            scores = [
                sum(weights[class_index][feature_id] for feature_id in active_feature_indexes)
                for class_index in range(class_count)
            ]
            max_score = max(scores)
            exp_scores = [
                math.exp(score - max_score)
                for score in scores
            ]
            exp_sum = sum(exp_scores)
            probabilities = [
                exp_score / exp_sum
                for exp_score in exp_scores
            ]

            for class_index in range(class_count):
                error = probabilities[class_index] - (
                    1.0 if class_index == target_index else 0.0
                )

                for feature_id in active_feature_indexes:
                    weights[class_index][feature_id] -= learning_rate * error

    return {
        "labels": labels,
        "feature_index": feature_index,
        "weights": weights
    }

def predict_container_with_model(filled_values, matching_containers):
    model = train_container_classifier()
    active_feature_indexes = [
        model["feature_index"][feature]
        for property_name, value in filled_values
        for feature in [make_model_feature(property_name, value)]
        if feature in model["feature_index"]
    ]

    bias_index = model["feature_index"]["__bias__"]
    active_feature_indexes.append(bias_index)

    scores = [
        sum(weights[feature_id] for feature_id in active_feature_indexes)
        for weights in model["weights"]
    ]
    max_score = max(scores)
    exp_scores = [
        math.exp(score - max_score)
        for score in scores
    ]
    exp_sum = sum(exp_scores)
    probabilities = [
        exp_score / exp_sum
        for exp_score in exp_scores
    ]

    matching_names = {
        normalize_container_name(container_name)
        for container_name in matching_containers
    }
    candidate_name_by_normalized_name = {
        normalize_container_name(container_name): container_name
        for container_name in matching_containers
    }
    candidates = [
        (
            candidate_name_by_normalized_name[normalize_container_name(label)],
            probabilities[index]
        )
        for index, label in enumerate(model["labels"])
        if normalize_container_name(label) in matching_names
    ]

    if not candidates:
        candidates = [
            (label, probabilities[index])
            for index, label in enumerate(model["labels"])
        ]

    label, probability = max(candidates, key=lambda item: item[1])
    candidate_probability_sum = sum(
        candidate_probability
        for _, candidate_probability in candidates
    )

    if candidate_probability_sum:
        probability = probability / candidate_probability_sum

    return {
        "container": label,
        "probability": probability * 100
    }

def get_container_values_for_matching():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.id,
                    c.name,
                    p.id,
                    p.name,
                    p.data_type,
                    cv.value
                FROM containers c
                LEFT JOIN container_values cv
                    ON cv.container_id = c.id
                LEFT JOIN properties p
                    ON p.id = cv.property_id
                ORDER BY c.id, p.id, cv.id;
            """)

            return cur.fetchall()

def values_match(user_value, container_value, property_type):
    if container_value is None:
        return False

    user_value = str(user_value).strip()
    container_value = str(container_value).strip()

    if property_type == "NUMBER":
        try:
            user_number = float(user_value.replace(",", "."))
        except ValueError:
            return False

        try:
            if ";" in container_value:
                from_value, to_value = container_value.split(";", 1)
                return (
                    float(from_value.replace(",", ".")) <= user_number
                    <= float(to_value.replace(",", "."))
                )

            return user_number == float(container_value.replace(",", "."))
        except ValueError:
            return False

    return user_value == container_value

def get_matching_result(properties):
    input_values = st.session_state.input_values
    property_by_id = {
        prop[0]: {
            "name": prop[1],
            "type": prop[2]
        }
        for prop in properties
    }

    containers = {}

    for (
        container_id,
        container_name,
        property_id,
        property_name,
        property_type,
        value
    ) in get_container_values_for_matching():
        if container_id not in containers:
            containers[container_id] = {
                "name": container_name,
                "values": {}
            }

        if property_id is not None:
            containers[container_id]["values"].setdefault(
                property_id,
                {
                    "name": property_name,
                    "type": property_type,
                    "values": []
                }
            )
            containers[container_id]["values"][property_id]["values"].append(value)

    matching_containers = []
    rejected_containers = []

    for container_data in containers.values():
        rejection_reason = None

        for property_id, user_value in input_values.items():
            property_data = property_by_id[property_id]
            container_property = container_data["values"].get(property_id)
            container_values = (
                container_property["values"]
                if container_property
                else []
            )

            has_match = any(
                values_match(
                    user_value,
                    container_value,
                    property_data["type"]
                )
                for container_value in container_values
            )

            if not has_match:
                rejection_reason = (
                    f"{container_data['name']} исключен, "
                    f"т.к. {property_data['name']} != {user_value}"
                )
                break

        if rejection_reason:
            rejected_containers.append(rejection_reason)
        else:
            matching_containers.append(container_data["name"])

    return matching_containers, rejected_containers

def render_matching_result_page(properties):
    filled_values = [
        (prop[1], st.session_state.input_values[prop[0]])
        for prop in properties
        if st.session_state.input_values.get(prop[0])
    ]

    matching_containers, rejected_containers = get_matching_result(properties)

    if (
        st.session_state.get("suggested_prediction")
        and normalize_container_name(
            st.session_state.suggested_prediction["container"]
        ) not in {
            normalize_container_name(container_name)
            for container_name in matching_containers
        }
    ):
        st.session_state.pop("suggested_prediction", None)

    col_answer, col_values, col_rejected = st.columns(3)

    with col_answer:
        st.subheader("Ответ:")
        st.divider()

        if matching_containers:
            for container_name in matching_containers:
                st.write(container_name)

            if st.button(
                "Определить предполагаемый",
                use_container_width=True
            ):
                st.session_state.suggested_prediction = predict_container_with_model(
                    filled_values,
                    matching_containers
                )

            if st.session_state.get("suggested_prediction"):
                prediction = st.session_state.suggested_prediction
                st.success(
                    f"Предполагаемый контейнер: {prediction['container']} "
                    f"({prediction['probability']:.1f}%)"
                )
        else:
            st.info("Подходящих контейнеров нет")

    with col_values:
        st.subheader("Значения:")
        st.divider()

        for prop_name, value in filled_values:
            st.write(f"{prop_name}: {value}")

    with col_rejected:
        st.subheader("Не подошли:")
        st.divider()

        if rejected_containers:
            for reason in rejected_containers:
                st.write(reason)
                st.divider()
        else:
            st.info("Неподходящих контейнеров нет")

    st.divider()

    _, button_col, _ = st.columns([1, 2, 1])

    with button_col:
        if st.button(
            "Вернуться к вводу исходных данных",
            use_container_width=True
        ):
            st.session_state.show_matching_result = False
            st.session_state.pop("suggested_prediction", None)
            st.rerun()

def render_input_values_page():
    st.header("Ввод исходных данных")

    properties = get_properties()

    if "input_values" not in st.session_state:
        st.session_state.input_values = {}

    if "selected_input_property_id" not in st.session_state and properties:
        st.session_state.selected_input_property_id = properties[0][0]

    if not properties:
        st.warning("Сначала добавьте свойства в редакторе базы знаний")
        return

    if st.session_state.get("show_matching_result", False):
        render_matching_result_page(properties)
        return

    property_ids = [prop[0] for prop in properties]
    selected_property_id = st.session_state.selected_input_property_id

    if selected_property_id not in property_ids:
        selected_property_id = property_ids[0]
        st.session_state.selected_input_property_id = selected_property_id

    selected_property = next(
        prop for prop in properties
        if prop[0] == selected_property_id
    )

    col_properties, col_value, col_summary = st.columns(3)

    with col_properties:
        st.subheader("Свойства:")
        st.divider()

        selected_property_name = st.radio(
            "Свойства",
            [prop[1] for prop in properties],
            index=property_ids.index(selected_property_id),
            label_visibility="collapsed",
            key="input_property_radio"
        )

        selected_property = next(
            prop for prop in properties
            if prop[1] == selected_property_name
        )
        st.session_state.selected_input_property_id = selected_property[0]

    with col_value:
        st.subheader("Значение:")
        st.divider()

        prop_id, prop_name, prop_type = selected_property
        current_value = st.session_state.input_values.get(prop_id, "")

        if prop_type == "NUMBER":
            new_value = st.text_input(
                "Введите число:",
                value=current_value,
                key=f"input_number_{prop_id}"
            )

            if new_value.strip():
                try:
                    float(new_value.replace(",", "."))
                    st.session_state.input_values[prop_id] = new_value.strip()
                except ValueError:
                    st.error("Введите число")
            else:
                st.session_state.input_values.pop(prop_id, None)

        elif prop_type == "ENUM":
            options = [option[1] for option in get_options(prop_id)]

            if options:
                select_options = [""] + options
                selected_index = (
                    select_options.index(current_value)
                    if current_value in select_options
                    else 0
                )

                new_value = st.selectbox(
                    "Введите значение:",
                    select_options,
                    index=selected_index,
                    key=f"input_enum_{prop_id}"
                )

                if new_value:
                    st.session_state.input_values[prop_id] = new_value
                else:
                    st.session_state.input_values.pop(prop_id, None)
            else:
                st.warning("Для этого свойства нет возможных значений")

        else:
            new_value = st.text_input(
                "Введите значение:",
                value=current_value,
                key=f"input_string_{prop_id}"
            )

            if new_value.strip():
                st.session_state.input_values[prop_id] = new_value.strip()
            else:
                st.session_state.input_values.pop(prop_id, None)

    with col_summary:
        st.subheader("Итог:")
        st.divider()

        filled_values = [
            (prop[1], st.session_state.input_values[prop[0]])
            for prop in properties
            if st.session_state.input_values.get(prop[0])
        ]

        if filled_values:
            for prop_name, value in filled_values:
                st.write(f"{prop_name}: {value}")
        else:
            st.info("Пока нет введенных значений")

    st.divider()

    button_col_1, button_col_2, _ = st.columns([2, 2, 1])

    with button_col_1:
        if st.button("Посмотреть базу знаний", use_container_width=True):
            st.session_state.open_editor_page = True
            st.rerun()

    with button_col_2:
        if st.button(
            "Определить вид контейнера",
            use_container_width=True,
            disabled=not bool(st.session_state.input_values)
        ):
            st.session_state.pop("suggested_prediction", None)
            st.session_state.show_matching_result = True
            st.rerun()

st.set_page_config(layout="wide")

menu_items = ["Виды контейнеров", "Свойства", "Возможные значения", "Описание свойств вида", "Значения для вида", "Проверка полноты знаний"]
page_items = ["Редактор базы знаний", "Ввод исходных чисел"]

if st.session_state.pop("open_editor_page", False):
    st.session_state.selected_page = "Редактор базы знаний"

selected_page = st.sidebar.radio(
    "Страница",
    page_items,
    key="selected_page"
)

if selected_page == "Редактор базы знаний":
    st.sidebar.title("Редактор базы знаний")
    selected_menu = st.sidebar.radio("Навигация", menu_items, index=2) # По умолчанию открываем Возможные значения
else:
    selected_menu = None

if selected_page == "Ввод исходных чисел":
    render_input_values_page()

elif selected_menu == "Виды контейнеров":
    st.header("Виды контейнеров")
    st.write("") # Отступ

    # 1. Вывод списка контейнеров
    containers = get_containers()
    for cont in containers:
        cont_id, cont_name = cont[0], cont[1]
        col1, col2 = st.columns([1, 10])
        with col1:
            if st.button("➖", key=f"del_cont_{cont_id}"):
                delete_container(cont_id)
                st.rerun()
        with col2:
            new_cont_name = st.text_input("Edit cont", value=cont_name, key=f"edit_cont_{cont_id}", label_visibility="collapsed")
            if new_cont_name != cont_name and new_cont_name.strip():
                if update_container(cont_id, new_cont_name.strip()):
                    st.rerun()
                else:
                    st.error(f"Контейнер '{new_cont_name}' уже существует!")

    st.divider()
    
    # 2. Добавление нового контейнера
    col_input, col_btn = st.columns([8, 2])
    with col_input:
        new_cont_val = st.text_input("Введите название контейнера", key="new_cont_input", label_visibility="collapsed", placeholder="Введите название контейнера")
    with col_btn:
        if st.button("Добавить", use_container_width=True, type="primary", key="add_cont_btn"):
            if new_cont_val.strip():
                if add_container(new_cont_val.strip()):
                    st.rerun()
                else:
                    st.error("Такой контейнер уже существует!")

elif selected_menu == "Свойства":
    st.header("Свойства")
    st.write("")

    type_map = {
        "ENUM": "Перечисление",
        "STRING": "Строка",
        "NUMBER": "Число"
    }

    reverse_type_map = {
        "Перечисление": "ENUM",
        "Строка": "STRING",
        "Число": "NUMBER"
    }

    # 1. Вывод списка свойств
    properties = get_properties()

    for prop in properties:
        prop_id, prop_name, prop_type = prop

        col1, col2, col3 = st.columns([1, 6, 3])

        with col1:
            if st.button("➖", key=f"del_prop_{prop_id}"):
                delete_property(prop_id)
                st.rerun()

        with col2:
            new_prop_name = st.text_input(
                "Edit prop",
                value=prop_name,
                key=f"edit_prop_{prop_id}",
                label_visibility="collapsed"
            )

            if new_prop_name != prop_name and new_prop_name.strip():
                try:
                    update_property_name(prop_id, new_prop_name.strip())
                    st.rerun()
                except:
                    st.error(f"Свойство '{new_prop_name}' уже существует!")

        with col3:
            current_type_ru = type_map.get(prop_type, "Строка")

            selected_type_ru = st.selectbox(
                "Тип",
                options=["Перечисление", "Строка", "Число"],
                index=["Перечисление", "Строка", "Число"].index(current_type_ru),
                key=f"type_{prop_id}",
                label_visibility="collapsed"
            )

            selected_type_db = reverse_type_map[selected_type_ru]

            if selected_type_db != prop_type:

                if (
                    selected_type_db == "NUMBER"
                    and property_has_non_numeric_values(prop_id)
                ):
                    st.error(
                        "Нельзя изменить тип на 'Число': "
                        "есть нечисловые значения"
                    )

                else:
                    update_property_type(prop_id, selected_type_db)
                    st.rerun()

    st.divider()

    # 2. Добавление нового свойства
    col_input, col_btn = st.columns([8, 2])

    with col_input:
        new_prop_val = st.text_input(
            "Введите название свойства",
            key="new_prop_input",
            label_visibility="collapsed",
            placeholder="Введите название свойства"
        )

    with col_btn:
        if st.button("Добавить", use_container_width=True, type="primary", key="add_prop_btn"):
            if new_prop_val.strip():
                if add_property(new_prop_val.strip()):
                    st.rerun()
                else:
                    st.error("Такое свойство уже существует!")

elif selected_menu == "Возможные значения":

    st.header("Возможные значения")
    
    properties = [
        p for p in get_properties()
        if p[2] == "ENUM"
    ]
    if not properties:
        st.warning("Сначала добавьте свойства в разделе 'Свойства'")
    else:
        prop_names = [p[1] for p in properties]
        prop_dict = {p[1]: p[0] for p in properties}
        
        selected_prop_name = st.radio("Свойства", prop_names, horizontal=True, label_visibility="collapsed")
        selected_prop_id = prop_dict[selected_prop_name]

        new_prop_name = st.text_input("Изменить название свойства:", value=selected_prop_name)
        if new_prop_name != selected_prop_name:
            update_property_name(selected_prop_id, new_prop_name)
            st.rerun()

        st.divider()
        st.subheader("Значения:")

        # 3. Вывод списка значений с возможностью редактирования и удаления
        options = get_options(selected_prop_id)
        for opt in options:
            opt_id, opt_value = opt[0], opt[1]
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button("➖", key=f"del_{opt_id}"):
                    delete_option(opt_id, selected_prop_id, opt_value)
                    st.rerun()
            with col2:
                # Поле ввода вместо обычного текста. Обновляется при Enter или потере фокуса
                new_opt_value = st.text_input("Edit", value=opt_value, key=f"edit_{opt_id}", label_visibility="collapsed")
                if new_opt_value != opt_value and new_opt_value.strip():
                    if update_option(opt_id, selected_prop_id, opt_value, new_opt_value.strip()):
                        st.rerun()
                    else:
                        st.error(f"Значение '{new_opt_value}' уже существует!")

        st.write("") # Отступ
        
        # 4. Добавление нового значения
        col_input, col_btn = st.columns([8, 2])
        with col_input:
            new_val = st.text_input("Введите название значения", key="new_val_input", label_visibility="collapsed", placeholder="Введите название значения")
        with col_btn:
            if st.button("Добавить", use_container_width=True, type="primary"):
                if new_val.strip():
                    if add_option(selected_prop_id, new_val.strip()):
                        st.rerun()
                    else:
                        st.error("Такое значение уже существует!")

elif selected_menu == "Описание свойств вида":

    st.header("Описание свойств вида")

    containers = get_containers()

    if not containers:
        st.warning("Нет контейнеров")
        st.stop()

    properties = get_properties()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Виды контейнеров")

        container_names = [c[1] for c in containers]

        selected_container_name = st.radio(
            "Контейнеры",
            container_names,
            label_visibility="collapsed"
        )

        selected_container_id = next(
            c[0] for c in containers
            if c[1] == selected_container_name
        )

    with col2:

        st.subheader("Свойства")

        container_properties = get_container_properties(
            selected_container_id
        )

        container_property_ids = [
            p[0] for p in container_properties
        ]

        for prop in properties:

            prop_id = prop[0]
            prop_name = prop[1]

            cols = st.columns([1, 10])

            if prop_id in container_property_ids:

                with cols[0]:
                    if st.button(
                        "➖",
                        key=f"remove_prop_{selected_container_id}_{prop_id}"
                    ):
                        remove_property_from_container(
                            selected_container_id,
                            prop_id
                        )
                        st.rerun()

                with cols[1]:
                    st.write(prop_name)

            else:

                with cols[0]:
                    if st.button(
                        "➕",
                        key=f"add_prop_{selected_container_id}_{prop_id}"
                    ):
                        add_property_to_container(
                            selected_container_id,
                            prop_id
                        )
                        st.rerun()

                with cols[1]:
                    st.write(prop_name)

elif selected_menu == "Значения для вида":

    st.header("Значения для вида")

    containers = get_containers()

    if not containers:
        st.warning("Нет контейнеров")
        st.stop()

    container_names = [c[1] for c in containers]

    selected_container_name = st.selectbox(
        "Контейнер",
        container_names,
        label_visibility="collapsed"
    )

    selected_container_id = next(
        c[0] for c in containers
        if c[1] == selected_container_name
    )

    container_properties = get_container_properties(
        selected_container_id
    )

    if not container_properties:
        st.warning("У контейнера нет свойств")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Свойства")

        property_names = [p[1] for p in container_properties]

        selected_property_name = st.radio(
            "Свойства",
            property_names,
            label_visibility="collapsed"
        )

        selected_property = next(
            p for p in container_properties
            if p[1] == selected_property_name
        )

        selected_property_id = selected_property[0]

    with col2:

        property_data = get_property_by_id(
            selected_property_id
        )

        property_type = property_data[2]

        st.subheader("Значения")

        current_values = get_container_property_values(
            selected_container_id,
            selected_property_id
        )

        if property_type == "ENUM":

            options = get_options(selected_property_id)

            option_values = [o[1] for o in options]

            selected_values = st.multiselect(
                "Значения",
                option_values,
                default=current_values,
                label_visibility="collapsed"
            )

            if set(selected_values) != set(current_values):

                delete_container_property_values(
                    selected_container_id,
                    selected_property_id
                )

                for value in selected_values:

                    set_container_property_value(
                        selected_container_id,
                        selected_property_id,
                        value
                    )

                st.rerun()

        elif property_type == "STRING":

            current_value = (
                current_values[0]
                if current_values
                else ""
            )

            new_value = st.text_input(
                "Значение",
                value=current_value,
                label_visibility="collapsed"
            )

            if new_value != current_value:

                delete_container_property_values(
                    selected_container_id,
                    selected_property_id
                )

                if new_value.strip():

                    set_container_property_value(
                        selected_container_id,
                        selected_property_id,
                        new_value.strip()
                    )

                st.rerun()

        elif property_type == "NUMBER":

            current_from = ""
            current_to = ""

            if current_values:

                parts = current_values[0].split(";")

                if len(parts) == 2:
                    current_from = parts[0]
                    current_to = parts[1]

            col1, col2 = st.columns(2)

            with col1:
                number_from = st.text_input(
                    "От",
                    value=current_from
                )

            with col2:
                number_to = st.text_input(
                    "До",
                    value=current_to
                )

            if (
                number_from != current_from
                or number_to != current_to
            ):

                try:

                    from_value = float(number_from)
                    to_value = float(number_to)

                    if from_value > to_value:
                        st.error(
                            "Левая граница должна быть меньше правой"
                        )

                    else:

                        delete_container_property_values(
                            selected_container_id,
                            selected_property_id
                        )

                        set_container_property_value(
                            selected_container_id,
                            selected_property_id,
                            f"{from_value};{to_value}"
                        )

                        st.rerun()

                except:
                    st.error("Введите числа")

elif selected_menu == "Проверка полноты знаний":

    st.header("Проверка полноты знаний")

    null_properties = get_null_properties()

    if not null_properties:

        st.success("Все поля заполнены")

    else:

        st.error("Есть незаполненные поля")

        grouped_data = {}

        for container_name, property_name in null_properties:

            if property_name not in grouped_data:
                grouped_data[property_name] = []

            grouped_data[property_name].append(
                container_name
            )

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("Свойства")

            for property_name in grouped_data.keys():
                st.write(property_name)

        with col2:

            st.subheader("Виды контейнеров")

            for containers in grouped_data.values():

                for container_name in containers:
                    st.write(container_name)

                st.write("")
