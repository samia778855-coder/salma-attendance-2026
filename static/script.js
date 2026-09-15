let currentStudents = [];
let selectedStudentIds = new Set();

let todayAbsenceRows = [];
let missingClasses = [];
let managementStudents = [];

let systemSettings = {
    school_name:
        "مدرسة سلمى بنت قيس للتعليم الأساسي (5–12)",

    academic_year:
        "2026/2027",

    absence_alert_limit:
        "8",

    daily_message:
        "",

    alert_message:
        ""
};


document.addEventListener(
    "DOMContentLoaded",
    async function () {

        setDefaultMonth();

        restoreTeacherName();

        document
            .getElementById("grade")
            .addEventListener(
                "change",
                loadClassStudents
            );

        document
            .getElementById("section")
            .addEventListener(
                "change",
                loadClassStudents
            );

        document
            .getElementById("studentSearch")
            .addEventListener(
                "input",
                renderStudentList
            );

        document
            .getElementById("saveAbsenceBtn")
            .addEventListener(
                "click",
                saveAbsence
            );

        document
            .getElementById("noAbsenceBtn")
            .addEventListener(
                "click",
                saveNoAbsence
            );

        document
            .getElementById("teacherName")
            .addEventListener(
                "change",
                rememberTeacherName
            );

        document
            .getElementById("managementSearch")
            .addEventListener(
                "keydown",
                function (event) {

                    if (event.key === "Enter") {
                        searchManagementStudents();
                    }

                }
            );

        await loadSettings();
        await refreshAll();

    }
);


/* =========================================================
   NAVIGATION
========================================================= */

function openSection(sectionId, button) {

    document
        .querySelectorAll(".page-section")
        .forEach(section => {
            section.classList.remove(
                "active-section"
            );
        });

    const target =
        document.getElementById(sectionId);

    if (target) {
        target.classList.add(
            "active-section"
        );
    }

    document
        .querySelectorAll(".nav-item")
        .forEach(item => {
            item.classList.remove("active");
        });

    if (button) {
        button.classList.add("active");
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

    if (sectionId === "dashboardSection") {
        loadDashboard();
        loadClassStatus();
    }

    if (sectionId === "todaySection") {
        loadTodayAbsences();
    }

    if (sectionId === "alertsSection") {
        loadAlerts();
    }

    if (sectionId === "settingsSection") {
        loadSettings();
    }

}


function openSectionByName(sectionId) {

    const button =
        document.querySelector(
            `.nav-item[data-section="${sectionId}"]`
        );

    openSection(
        sectionId,
        button
    );

}


function openStudentTab(tabId, button) {

    document
        .querySelectorAll(".student-tab")
        .forEach(tab => {
            tab.classList.remove("active");
        });

    document
        .querySelectorAll(".subtab")
        .forEach(item => {
            item.classList.remove("active");
        });

    document
        .getElementById(tabId)
        .classList.add("active");

    button.classList.add("active");

    if (tabId === "phonesTab") {
        loadMissingPhones();
    }

}


/* =========================================================
   GENERAL
========================================================= */

function showMessage(message, type = "success") {

    const box =
        document.getElementById(
            "messageBox"
        );

    box.textContent = message;

    box.className =
        "toast " +
        (
            type === "success"
                ? "message-success"
                : "message-error"
        );

    box.classList.remove("hidden");

    setTimeout(
        function () {
            box.classList.add("hidden");
        },
        4500
    );

}


async function refreshAll() {

    await Promise.all([
        loadDashboard(),
        loadTodayAbsences(),
        loadAlerts(),
        loadClassStatus()
    ]);

}


function setDefaultMonth() {

    const today =
        new Date();

    const value =
        today.getFullYear() +
        "-" +
        String(
            today.getMonth() + 1
        ).padStart(2, "0");

    const monthInput =
        document.getElementById(
            "reportMonth"
        );

    if (
        monthInput &&
        !monthInput.value
    ) {
        monthInput.value = value;
    }

}


function rememberTeacherName() {

    const name =
        document
            .getElementById("teacherName")
            .value
            .trim();

    if (name) {
        localStorage.setItem(
            "attendance_teacher_name",
            name
        );
    }

}


function restoreTeacherName() {

    const saved =
        localStorage.getItem(
            "attendance_teacher_name"
        );

    if (saved) {
        document
            .getElementById("teacherName")
            .value = saved;
    }

}


/* =========================================================
   DASHBOARD
========================================================= */

async function loadDashboard() {

    try {

        const response =
            await fetch("/api/dashboard");

        const data =
            await response.json();

        document.getElementById(
            "totalStudents"
        ).textContent =
            data.total_students;

        document.getElementById(
            "absentToday"
        ).textContent =
            data.absent_today;

        document.getElementById(
            "absencePercentage"
        ).textContent =
            data.absence_percentage + "%";

        document.getElementById(
            "registeredClasses"
        ).textContent =
            data.registered_classes;

        document.getElementById(
            "unregisteredClasses"
        ).textContent =
            data.unregistered_count;

        document.getElementById(
            "alertCount"
        ).textContent =
            data.alerts;

        document.getElementById(
            "completionPercentage"
        ).textContent =
            data.completion_percentage + "%";

        document.getElementById(
            "progressRegistered"
        ).textContent =
            data.registered_classes;

        document.getElementById(
            "progressTotal"
        ).textContent =
            data.total_classes;

        document.getElementById(
            "quickRegistered"
        ).textContent =
            data.registered_classes;

        document.getElementById(
            "quickTotalClasses"
        ).textContent =
            data.total_classes;

        document.getElementById(
            "quickMissing"
        ).textContent =
            data.unregistered_count;

        document.getElementById(
            "quickAbsentToday"
        ).textContent =
            data.absent_today;

        document.getElementById(
            "todayNavBadge"
        ).textContent =
            data.absent_today;

        document.getElementById(
            "alertsNavBadge"
        ).textContent =
            data.alerts;

        document.getElementById(
            "missingCountBadge"
        ).textContent =
            data.unregistered_count;

        document.getElementById(
            "dashboardProgress"
        ).style.width =
            data.completion_percentage + "%";

        document.getElementById(
            "quickProgressBar"
        ).style.width =
            data.completion_percentage + "%";

        missingClasses =
            data.unregistered_classes || [];

        renderMissingClasses();

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

    }

}


function renderMissingClasses() {

    const dashboardContainer =
        document.getElementById(
            "missingClassesGrid"
        );

    const modalContainer =
        document.getElementById(
            "modalMissingClasses"
        );

    if (!missingClasses.length) {

        const complete = `
            <div class="empty-state">
                ✅ تم استكمال تسجيل جميع الصفوف اليوم.
            </div>
        `;

        dashboardContainer.innerHTML =
            complete;

        modalContainer.innerHTML =
            complete;

        return;
    }

    const html =
        missingClasses
            .map(
                item => `
                    <span class="class-chip">
                        ${escapeHtml(item.grade_name)}
                        /
                        ${escapeHtml(item.section)}
                    </span>
                `
            )
            .join("");

    dashboardContainer.innerHTML =
        html;

    modalContainer.innerHTML =
        html;

}


async function loadClassStatus() {

    const body =
        document.getElementById(
            "classStatusTable"
        );

    try {

        const response =
            await fetch(
                "/api/class-status"
            );

        const rows =
            await response.json();

        if (!rows.length) {

            body.innerHTML = `
                <tr>
                    <td colspan="4">
                        لا توجد صفوف مسجلة في بيانات الطالبات.
                    </td>
                </tr>
            `;

            return;
        }

        body.innerHTML =
            rows
                .map(
                    row => {

                        const status =
                            row.registered
                                ? (
                                    row.no_absence
                                        ? `
                                            <span class="status status-success">
                                                ✅ لا يوجد غياب
                                            </span>
                                          `
                                        : `
                                            <span class="status status-success">
                                                ✅ تم التسجيل
                                            </span>
                                          `
                                )
                                : `
                                    <span class="status status-warning">
                                        ⏳ لم يسجل
                                    </span>
                                  `;

                        return `
                            <tr>

                                <td>
                                    ${escapeHtml(row.grade_name)}
                                    /
                                    ${escapeHtml(row.section)}
                                </td>

                                <td>
                                    ${status}
                                </td>

                                <td>
                                    ${
                                        row.teacher_name
                                            ? escapeHtml(
                                                row.teacher_name
                                            )
                                            : "-"
                                    }
                                </td>

                                <td>
                                    ${
                                        row.created_at
                                            ? formatTime(
                                                row.created_at
                                            )
                                            : "-"
                                    }
                                </td>

                            </tr>
                        `;

                    }
                )
                .join("");

    } catch (error) {

        body.innerHTML = `
            <tr>
                <td colspan="4">
                    تعذر تحميل حالة الصفوف.
                </td>
            </tr>
        `;

    }

}


/* =========================================================
   ATTENDANCE REGISTRATION
========================================================= */

async function loadClassStudents() {

    const grade =
        document.getElementById(
            "grade"
        ).value;

    const section =
        document.getElementById(
            "section"
        ).value;

    currentStudents = [];
    selectedStudentIds.clear();

    renderSelectedStudents();

    if (!grade || !section) {

        document.getElementById(
            "studentList"
        ).innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    👩‍🎓
                </div>

                اختاري المرحلة والشعبة لعرض الطالبات.

            </div>
        `;

        return;
    }

    try {

        const response =
            await fetch(
                `/api/students?grade=${encodeURIComponent(grade)}&section=${encodeURIComponent(section)}`
            );

        currentStudents =
            await response.json();

        renderStudentList();

    } catch (error) {

        showMessage(
            "تعذر تحميل أسماء الطالبات.",
            "error"
        );

    }

}


function renderStudentList() {

    const container =
        document.getElementById(
            "studentList"
        );

    const search =
        document
            .getElementById(
                "studentSearch"
            )
            .value
            .trim()
            .toLowerCase();

    const filtered =
        currentStudents.filter(
            student =>
                student.student_name
                    .toLowerCase()
                    .includes(search)
        );

    if (!filtered.length) {

        container.innerHTML = `
            <div class="empty-state">
                لا توجد طالبات مطابقة.
            </div>
        `;

        return;
    }

    container.innerHTML =
        filtered
            .map(
                student => {

                    const checked =
                        selectedStudentIds.has(
                            student.id
                        )
                            ? "checked"
                            : "";

                    return `
                        <label class="student-item">

                            <input
                                type="checkbox"
                                ${checked}
                                onchange="toggleStudent(${student.id})"
                            >

                            <span class="student-item-name">
                                ${escapeHtml(student.student_name)}
                            </span>

                        </label>
                    `;

                }
            )
            .join("");

}


function toggleStudent(studentId) {

    if (selectedStudentIds.has(studentId)) {
        selectedStudentIds.delete(studentId);
    } else {
        selectedStudentIds.add(studentId);
    }

    renderSelectedStudents();

}


function clearSelectedStudents() {

    selectedStudentIds.clear();

    renderStudentList();
    renderSelectedStudents();

}


function renderSelectedStudents() {

    document.getElementById(
        "selectedCount"
    ).textContent =
        selectedStudentIds.size;

    const container =
        document.getElementById(
                        "selectedStudents"
        );

    if (!selectedStudentIds.size) {

        container.innerHTML = "";

        return;
    }

    const students =
        currentStudents.filter(
            student =>
                selectedStudentIds.has(
                    student.id
                )
        );

    container.innerHTML =
        students
            .map(
                student => `
                    <span class="selected-tag">
                        ${escapeHtml(student.student_name)}
                    </span>
                `
            )
            .join("");

}


async function saveAbsence() {

    const grade =
        document.getElementById(
            "grade"
        ).value;

    const section =
        document.getElementById(
            "section"
        ).value;

    const teacherName =
        document
            .getElementById(
                "teacherName"
            )
            .value
            .trim();

    if (!grade || !section) {

        showMessage(
            "اختاري المرحلة والشعبة أولًا.",
            "error"
        );

        return;
    }

    if (!selectedStudentIds.size) {

        showMessage(
            "حددي طالبة غائبة واحدة على الأقل.",
            "error"
        );

        return;
    }

    if (!teacherName) {

        showMessage(
            "اكتبي اسم المعلمة.",
            "error"
        );

        return;
    }

    rememberTeacherName();

    const confirmed =
        confirm(
            `سيتم تسجيل ${selectedStudentIds.size} طالبة غائبة. هل تريدين المتابعة؟`
        );

    if (!confirmed) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/register-absence",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            grade:
                                grade,

                            section:
                                section,

                            teacher_name:
                                teacherName,

                            student_ids:
                                Array.from(
                                    selectedStudentIds
                                )
                        })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            showMessage(
                data.message,
                "error"
            );

            return;
        }

        showMessage(
            `${data.message} عدد الغائبات: ${data.absence_count}`
        );

        selectedStudentIds.clear();

        document.getElementById(
            "studentSearch"
        ).value = "";

        renderSelectedStudents();
        renderStudentList();

        await refreshAll();

    } catch (error) {

        showMessage(
            "حدث خطأ أثناء حفظ الغياب.",
            "error"
        );

    }

}


async function saveNoAbsence() {

    const grade =
        document.getElementById(
            "grade"
        ).value;

    const section =
        document.getElementById(
            "section"
        ).value;

    const teacherName =
        document
            .getElementById(
                "teacherName"
            )
            .value
            .trim();

    if (!grade || !section) {

        showMessage(
            "اختاري المرحلة والشعبة.",
            "error"
        );

        return;
    }

    if (!teacherName) {

        showMessage(
            "اكتبي اسم المعلمة.",
            "error"
        );

        return;
    }

    const confirmed =
        confirm(
            "تأكيد أن الصف مكتمل الحضور ولا يوجد غياب؟"
        );

    if (!confirmed) {
        return;
    }

    rememberTeacherName();

    try {

        const response =
            await fetch(
                "/api/no-absence",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            grade:
                                grade,

                            section:
                                section,

                            teacher_name:
                                teacherName
                        })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            showMessage(
                data.message,
                "error"
            );

            return;
        }

        showMessage(
            data.message
        );

        selectedStudentIds.clear();

        renderSelectedStudents();
        renderStudentList();

        await refreshAll();

    } catch (error) {

        showMessage(
            "تعذر حفظ التسجيل.",
            "error"
        );

    }

}


/* =========================================================
   TODAY ABSENCES
========================================================= */

async function loadTodayAbsences() {

    try {

        const response =
            await fetch(
                "/api/today-absences"
            );

        todayAbsenceRows =
            await response.json();

        document.getElementById(
            "todayCountLabel"
        ).textContent =
            todayAbsenceRows.length;

        renderTodayAbsences();

    } catch (error) {

        document.getElementById(
            "todayAbsenceTable"
        ).innerHTML = `
            <tr>
                <td colspan="8">
                    تعذر تحميل البيانات.
                </td>
            </tr>
        `;

    }

}


function renderTodayAbsences() {

    const body =
        document.getElementById(
            "todayAbsenceTable"
        );

    const search =
        document
            .getElementById(
                "todaySearch"
            )
            .value
            .trim()
            .toLowerCase();

    const rows =
        todayAbsenceRows.filter(
            row =>
                row.student_name
                    .toLowerCase()
                    .includes(search)
        );

    if (!rows.length) {

        body.innerHTML = `
            <tr>
                <td colspan="8">
                    لا توجد نتائج.
                </td>
            </tr>
        `;

        return;
    }

    body.innerHTML =
        rows
            .map(
                (row, index) => {

                    const whatsapp =
                        buildDailyWhatsAppButtons(
                            row
                        );

                    const statusClass =
                        row.absence_status ===
                        "بعذر"
                            ? "status-success"
                            : (
                                row.absence_status ===
                                "بدون عذر"
                                    ? "status-danger"
                                    : "status-warning"
                            );

                    return `
                        <tr>

                            <td>
                                ${index + 1}
                            </td>

                            <td>
                                <strong>
                                    ${escapeHtml(row.student_name)}
                                </strong>
                            </td>

                            <td>
                                ${row.grade}/${row.section}
                            </td>

                            <td>
                                ${escapeHtml(row.teacher_name)}
                            </td>

                            <td>
                                ${formatTime(row.created_at)}
                            </td>

                            <td>

                                <span class="status ${statusClass}">
                                    ${escapeHtml(row.absence_status || "مسجل")}
                                </span>

                            </td>

                            <td>
                                ${whatsapp}
                            </td>

                            <td>

                                <button
                                    class="btn btn-danger-soft"
                                    onclick="deleteAttendance(
                                        ${row.attendance_id},
                                        '${escapeJs(row.student_name)}'
                                    )"
                                >
                                    حذف
                                </button>

                            </td>

                        </tr>
                    `;

                }
            )
            .join("");

}


function buildDailyWhatsAppButtons(row) {

    const template =
        systemSettings.daily_message ||
        "نود إفادتكم أن ابنتكم ({student}) قد تغيبت اليوم بتاريخ ({date}).";

    const message =
        template
            .replaceAll(
                "{student}",
                row.student_name
            )
            .replaceAll(
                "{date}",
                row.attendance_date
            );

    const buttons = [];

    if (
        row.mother_phone &&
        row.mother_phone_status ===
        "متوفر"
    ) {

        buttons.push(
            whatsappButton(
                row.student_id,
                row.mother_phone,
                message,
                "الأم",
                "غياب يومي"
            )
        );

    }

    if (
        row.father_phone &&
        row.father_phone_status ===
        "متوفر"
    ) {

        buttons.push(
            whatsappButton(
                row.student_id,
                row.father_phone,
                message,
                "الأب",
                "غياب يومي"
            )
        );

    }

    if (!buttons.length) {

        return `
            <span class="btn btn-disabled">
                الرقم غير متوفر
            </span>
        `;

    }

    return buttons.join(" ");

}


/* =========================================================
   WHATSAPP WEB
========================================================= */

function whatsappButton(
    studentId,
    phone,
    message,
    phoneType,
    notificationType
) {

    const normalized =
        normalizePhoneForWhatsApp(
            phone
        );

    if (!normalized) {

        return `
            <span class="btn btn-disabled">
                ${phoneType}: غير متوفر
            </span>
        `;

    }

    const url =
        "https://api.whatsapp.com/send" +
        "?phone=" +
        encodeURIComponent(normalized) +
        "&text=" +
        encodeURIComponent(message);

    return `
        <a
            href="${url}"
            target="_blank"
            rel="noopener noreferrer"
            class="btn btn-whatsapp"
            onclick="logNotification(
                ${studentId},
                '${escapeJs(notificationType)}',
                '${escapeJs(phoneType)}',
                '${escapeJs(phone)}'
            )"
        >
            واتساب ${phoneType}
        </a>
    `;

}


async function logNotification(
    studentId,
    notificationType,
    phoneType,
    phoneNumber
) {

    try {

        await fetch(
            "/api/log-notification",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body:
                    JSON.stringify({
                        student_id:
                            studentId,

                        notification_type:
                            notificationType,

                        phone_type:
                            phoneType,

                        phone_number:
                            phoneNumber
                    })
            }
        );

    } catch (error) {

        console.error(error);

    }

}


async function deleteAttendance(
    attendanceId,
    studentName
) {

    const confirmed =
        confirm(
            `هل أنتِ متأكدة من حذف غياب الطالبة ${studentName}؟`
        );

    if (!confirmed) {
        return;
    }

    try {

        const response =
            await fetch(
                `/api/attendance/${attendanceId}`,
                {
                    method: "DELETE"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            showMessage(
                data.message,
                "error"
            );

            return;
        }

        showMessage(
            data.message
        );

        await refreshAll();

    } catch (error) {

        showMessage(
            "تعذر حذف السجل.",
            "error"
        );

    }

}


function exportToday() {

    window.location.href =
        `/export-excel?type=daily&date=${encodeURIComponent(TODAY)}`;

}


/* =========================================================
   ALERTS
========================================================= */

async function loadAlerts() {

    const body =
        document.getElementById(
            "alertsTable"
        );

    try {

        const response =
            await fetch(
                "/api/alerts"
            );

        const rows =
            await response.json();

        document.getElementById(
            "alertsNavBadge"
        ).textContent =
            rows.length;

        if (!rows.length) {

            body.innerHTML = `
                <tr>
                    <td colspan="8">
                        ✅ لا توجد طالبات تجاوزن حد الإنذار حاليًا.
                    </td>
                </tr>
            `;

            return;
        }

        body.innerHTML =
            rows
                .map(
                    (row, index) => {

                        const template =
                            systemSettings.alert_message ||
                            "نود إفادتكم أن ابنتكم ({student}) قد تجاوزت عدد الغياب {limit} أيام.";

                        const message =
                            template
                                .replaceAll(
                                    "{student}",
                                    row.student_name
                                )
                                .replaceAll(
                                    "{limit}",
                                    ALERT_LIMIT
                                );

                        const mother =
                            row.mother_phone_status ===
                            "متوفر"

                                ? whatsappButton(
                                    row.id,
                                    row.mother_phone,
                                    message,
                                    "الأم",
                                    "إنذار غياب"
                                )

                                : `
                                    <span class="btn btn-disabled">
                                        غير متوفر
                                    </span>
                                  `;
        
const father =
    row.father_phone_status ===
    "متوفر"

        ? whatsappButton(
            row.id,
            row.father_phone,
            message,
            "الأب",
            "إنذار غياب"
        )

        : `
            <span class="btn btn-disabled">
                غير متوفر
            </span>
          `;

return `
    <tr>

        <td>
            ${index + 1}
        </td>

        <td>
            <strong>
                ${escapeHtml(row.student_name)}
            </strong>
        </td>

        <td>
            ${row.grade}/${row.section}
        </td>

        <td>
            <strong>
                ${row.absence_count}
            </strong>
        </td>

        <td>
            ${row.last_absence || "-"}
        </td>

        <td>
            <span class="alert-badge">
                🔴 يحتاج متابعة
            </span>
        </td>

        <td>
            ${mother}
        </td>

        <td>
            ${father}
        </td>

    </tr>
`;

}
)
.join("");

} catch (error) {

body.innerHTML = `
    <tr>
        <td colspan="8">
            تعذر تحميل التنبيهات.
        </td>
    </tr>
`;

}

}


/* =========================================================
   REPORTS
========================================================= */

async function loadReport() {

const type =
document.getElementById(
    "reportType"
).value;

const reportDate =
document.getElementById(
    "reportDate"
).value;

const month =
document.getElementById(
    "reportMonth"
).value;

const grade =
document.getElementById(
    "reportGrade"
).value;

const section =
document.getElementById(
    "reportSection"
).value;

const url =
`/api/reports?type=${encodeURIComponent(type)}` +
`&date=${encodeURIComponent(reportDate)}` +
`&month=${encodeURIComponent(month)}` +
`&grade=${encodeURIComponent(grade)}` +
`&section=${encodeURIComponent(section)}`;

try {

const response =
    await fetch(url);

const rows =
    await response.json();

renderReport(
    type,
    rows
);

} catch (error) {

showMessage(
    "تعذر تحميل التقرير.",
    "error"
);

}

}


function renderReport(type, rows) {

const head =
document.getElementById(
    "reportHead"
);

const body =
document.getElementById(
    "reportBody"
);

const summary =
document.getElementById(
    "reportSummary"
);

const visual =
document.getElementById(
    "reportVisual"
);

visual.innerHTML = "";
visual.classList.add("hidden");

if (!rows.length) {

summary.textContent =
    "لا توجد بيانات مطابقة.";

head.innerHTML = "";

body.innerHTML = `
    <tr>
        <td>
            لا توجد بيانات لهذا التقرير.
        </td>
    </tr>
`;

return;
}

if (type === "daily") {

summary.textContent =
    `عدد الغائبات: ${rows.length}`;

head.innerHTML = `
    <tr>
        <th>#</th>
        <th>اسم الطالبة</th>
        <th>الصف</th>
        <th>التاريخ</th>
        <th>المعلمة</th>
        <th>الحالة</th>
        <th>الملاحظة</th>
    </tr>
`;

body.innerHTML =
    rows
        .map(
            (row, index) => `
                <tr>

                    <td>
                        ${index + 1}
                    </td>

                    <td>
                        ${escapeHtml(row.student_name)}
                    </td>

                    <td>
                        ${row.grade}/${row.section}
                    </td>

                    <td>
                        ${row.attendance_date}
                    </td>

                    <td>
                        ${escapeHtml(row.teacher_name)}
                    </td>

                    <td>
                        ${escapeHtml(row.absence_status || "مسجل")}
                    </td>

                    <td>
                        ${escapeHtml(row.note || "-")}
                    </td>

                </tr>
            `
        )
        .join("");

}


if (type === "monthly") {

summary.textContent =
    `عدد الطالبات اللاتي لديهن غياب خلال الشهر: ${rows.length}`;

head.innerHTML = `
    <tr>
        <th>#</th>
        <th>اسم الطالبة</th>
        <th>الصف</th>
        <th>تواريخ الغياب</th>
        <th>عدد الأيام</th>
    </tr>
`;

body.innerHTML =
    rows
        .map(
            (row, index) => `
                <tr>

                    <td>
                        ${index + 1}
                    </td>

                    <td>
                        ${escapeHtml(row.student_name)}
                    </td>

                    <td>
                        ${row.grade}/${row.section}
                    </td>

                    <td>
                        ${escapeHtml(row.absence_dates || "")}
                    </td>

                    <td>
                        <strong>
                            ${row.absence_count}
                        </strong>
                    </td>

                </tr>
            `
        )
        .join("");

}


if (type === "classes") {

const highest = rows[0];

const lowest =
    rows[rows.length - 1];

summary.innerHTML =
    `🔺 الأعلى: <strong>${highest.grade}/${highest.section}</strong> (${highest.absence_count})` +
    ` &nbsp;&nbsp; | &nbsp;&nbsp; ` +
    `🔻 الأقل: <strong>${lowest.grade}/${lowest.section}</strong> (${lowest.absence_count})`;

head.innerHTML = `
    <tr>
        <th>الترتيب</th>
        <th>الصف</th>
        <th>عدد حالات الغياب</th>
    </tr>
`;

body.innerHTML =
    rows
        .map(
            (row, index) => `
                <tr>

                    <td>
                        ${index + 1}
                    </td>

                    <td>
                        ${row.grade}/${row.section}
                    </td>

                    <td>
                        <strong>
                            ${row.absence_count}
                        </strong>
                    </td>

                </tr>
            `
        )
        .join("");

renderVisualBars(
    rows.map(
        row => ({
            label:
                `${row.grade}/${row.section}`,

            value:
                row.absence_count
        })
    )
);

}


if (type === "students") {

summary.textContent =
    "ترتيب الطالبات حسب عدد أيام الغياب خلال العام الدراسي.";

head.innerHTML = `
    <tr>
        <th>الترتيب</th>
        <th>اسم الطالبة</th>
        <th>الصف</th>
        <th>أيام الغياب</th>
        <th>آخر غياب</th>
    </tr>
`;

body.innerHTML =
    rows
        .map(
            (row, index) => `
                <tr>

                    <td>
                        ${index + 1}
                    </td>

                    <td>
                        ${escapeHtml(row.student_name)}
                    </td>

                    <td>
                        ${row.grade}/${row.section}
                    </td>

                    <td>
                        <strong>
                            ${row.absence_count}
                        </strong>
                    </td>

                    <td>
                        ${row.last_absence || "-"}
                    </td>

                </tr>
            `
        )
        .join("");

renderVisualBars(
    rows
        .slice(0, 10)
        .map(
            row => ({
                label:
                    row.student_name,

                value:
                    row.absence_count
            })
        )
);

}


if (type === "weekday") {

summary.textContent =
    "تحليل حالات الغياب حسب أيام الأسبوع.";

head.innerHTML = `
    <tr>
        <th>اليوم</th>
        <th>عدد حالات الغياب</th>
    </tr>
`;

body.innerHTML =
    rows
        .map(
            row => `
                <tr>

                    <td>
                        ${escapeHtml(row.weekday_name)}
                    </td>

                    <td>
                        <strong>
                            ${row.absence_count}
                        </strong>
                    </td>

                </tr>
            `
        )
        .join("");

renderVisualBars(
    rows.map(
        row => ({
            label:
                row.weekday_name,

            value:
                row.absence_count
        })
    )
);

}

}


function renderVisualBars(rows) {

const visual =
document.getElementById(
    "reportVisual"
);

if (!rows.length) {
return;
}

const maxValue =
Math.max(
    ...rows.map(
        row =>
            Number(row.value) || 0
    ),
    1
);

visual.innerHTML =
rows
    .map(
        row => {

            const width =
                Math.round(
                    (
                        Number(row.value) /
                        maxValue
                    ) * 100
                );

            return `
                <div class="visual-row">

                    <span>
                        ${escapeHtml(row.label)}
                    </span>

                    <div class="visual-bar">

                        <div
                            class="visual-fill"
                            style="width:${width}%"
                        ></div>

                    </div>

                    <strong>
                        ${row.value}
                    </strong>

                </div>
            `;

        }
    )
    .join("");

visual.classList.remove("hidden");

}


function exportReport() {

const type =
document.getElementById(
    "reportType"
).value;

const reportDate =
document.getElementById(
    "reportDate"
).value;

const month =
document.getElementById(
    "reportMonth"
).value;

if (
type !== "daily" &&
type !== "monthly"
) {

showMessage(
    "Excel متاح حاليًا للتقرير اليومي والشهري.",
    "error"
);

return;
}

window.location.href =
`/export-excel?type=${encodeURIComponent(type)}` +
`&date=${encodeURIComponent(reportDate)}` +
`&month=${encodeURIComponent(month)}`;

}


/* =========================================================
   STUDENT MANAGEMENT
========================================================= */                            
async function searchManagementStudents() {

    const query =
        document
            .getElementById(
                "managementSearch"
            )
            .value
            .trim();

    const container =
        document.getElementById(
            "managementResults"
        );

    if (!query) {

        container.innerHTML = `
            <div class="empty-state">
                اكتبي اسم الطالبة.
            </div>
        `;

        return;
    }

    try {

        const response =
            await fetch(
                `/api/student-search?q=${encodeURIComponent(query)}`
            );

        managementStudents =
            await response.json();

        if (!managementStudents.length) {

            container.innerHTML = `
                <div class="empty-state">
                    لم يتم العثور على طالبة بهذا الاسم.
                </div>
            `;

            return;
        }

        container.innerHTML =
            managementStudents
                .map(
                    student => `
                        <div class="management-result-item">

                            <div>
                                <strong>
                                    ${escapeHtml(student.student_name)}
                                </strong>

                                <small>
                                    الصف ${student.grade}/${student.section}
                                </small>
                            </div>

                            <div>
                                الغياب:
                                <strong>
                                    ${student.absence_count}
                                </strong>
                            </div>

                            <div>
                                آخر غياب:
                                <strong>
                                    ${student.last_absence || "-"}
                                </strong>
                            </div>

                            <div>
                                الأم:
                                <strong>
                                    ${student.mother_phone || "-"}
                                </strong>
                            </div>

                            <div>
                                الأب:
                                <strong>
                                    ${student.father_phone || "-"}
                                </strong>
                            </div>

                            <button
                                class="btn btn-primary-soft"
                                onclick="openStudentEdit(${student.id})"
                            >
                                تعديل
                            </button>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        container.innerHTML = `
            <div class="empty-state">
                حدث خطأ أثناء البحث.
            </div>
        `;

    }

}


function openStudentEdit(studentId) {

    const student =
        managementStudents.find(
            item =>
                item.id === studentId
        );

    if (!student) {
        return;
    }

    document.getElementById(
        "editStudentId"
    ).value =
        student.id;

    document.getElementById(
        "editStudentName"
    ).value =
        student.student_name;

    document.getElementById(
        "editGrade"
    ).value =
        student.grade;

    document.getElementById(
        "editSection"
    ).value =
        student.section;

    document.getElementById(
        "editFatherPhone"
    ).value =
        student.father_phone || "";

    document.getElementById(
        "editMotherPhone"
    ).value =
        student.mother_phone || "";

    document.getElementById(
        "studentEditModal"
    ).classList.remove("hidden");

}


async function saveStudentEdit() {

    const studentId =
        document.getElementById(
            "editStudentId"
        ).value;

    const payload = {
        student_name:
            document
                .getElementById(
                    "editStudentName"
                )
                .value
                .trim(),

        grade:
            document
                .getElementById(
                    "editGrade"
                )
                .value,

        section:
            document
                .getElementById(
                    "editSection"
                )
                .value,

        father_phone:
            normalizeLocalPhone(
                document
                    .getElementById(
                        "editFatherPhone"
                    )
                    .value
            ),

        mother_phone:
            normalizeLocalPhone(
                document
                    .getElementById(
                        "editMotherPhone"
                    )
                    .value
            )
    };

    try {

        const response =
            await fetch(
                `/api/student/${studentId}`,
                {
                    method: "PUT",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            showMessage(
                data.message,
                "error"
            );

            return;
        }

        showMessage(
            data.message
        );

        closeModal(
            "studentEditModal"
        );

        await searchManagementStudents();
        await refreshAll();

    } catch (error) {

        showMessage(
            "تعذر حفظ التعديلات.",
            "error"
        );

    }

}


async function deactivateCurrentStudent() {

    const studentId =
        document.getElementById(
            "editStudentId"
        ).value;

    const studentName =
        document
            .getElementById(
                "editStudentName"
            )
            .value;

    const confirmed =
        confirm(
            `سيتم تعطيل الطالبة ${studentName} من القوائم مع الاحتفاظ بسجل غيابها. هل تريدين المتابعة؟`
        );

    if (!confirmed) {
        return;
    }

    try {

        const response =
            await fetch(
                `/api/student/${studentId}/deactivate`,
                {
                    method: "PUT"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            showMessage(
                data.message,
                "error"
            );

            return;
        }

        showMessage(
            data.message
        );

        closeModal(
            "studentEditModal"
        );

        await searchManagementStudents();
        await refreshAll();

    } catch (error) {

        showMessage(
            "تعذر تنفيذ العملية.",
            "error"
        );

    }

}


async function addNewStudent() {

    const payload = {
        student_name:
            document
                .getElementById(
                    "newStudentName"
                )
                .value
                .trim(),

        grade:
            document
                .getElementById(
                    "newGrade"
                )
                .value,

        section:
            document
                .getElementById(
                    "newSection"
                )
                .value,

        father_phone:
            normalizeLocalPhone(
                document
                    .getElementById(
                        "newFatherPhone"
                    )
                    .value
            ),

        mother_phone:
            normalizeLocalPhone(
                document
                    .getElementById(
                        "newMotherPhone"
                    )
                    .value
            )
    };

    if (
        !payload.student_name ||
        !payload.grade ||
        !payload.section
    ) {

        showMessage(
            "أكملي اسم الطالبة والمرحلة والشعبة.",
            "error"
        );

        return;
    }

    try {

        const response =
            await fetch(
                "/api/student",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            showMessage(
                data.message,
                "error"
            );

            return;
        }

        showMessage(
            data.message
        );

        document.getElementById(
            "newStudentName"
        ).value = "";

        document.getElementById(
            "newFatherPhone"
        ).value = "";

        document.getElementById(
            "newMotherPhone"
        ).value = "";

        await refreshAll();

    } catch (error) {

        showMessage(
            "تعذر إضافة الطالبة.",
            "error"
        );

    }

}


async function loadMissingPhones() {

    const container =
        document.getElementById(
            "missingPhonesResults"
        );

    container.innerHTML = `
        <div class="empty-state">
            جاري تحميل البيانات...
        </div>
    `;

    try {

        const response =
            await fetch(
                "/api/missing-phones"
            );

        const rows =
            await response.json();

        if (!rows.length) {

            container.innerHTML = `
                <div class="empty-state">
                    ✅ جميع أرقام الهواتف مكتملة.
                </div>
            `;

            return;
        }

        container.innerHTML = `
            <table>

                <thead>
                    <tr>
                        <th>#</th>
                        <th>اسم الطالبة</th>
                        <th>الصف</th>
                        <th>هاتف الأب</th>
                        <th>حالة الأب</th>
                        <th>هاتف الأم</th>
                        <th>حالة الأم</th>
                    </tr>
                </thead>

                <tbody>

                    ${
                        rows
                            .map(
                                (row, index) => `
                                    <tr>

                                        <td>
                                            ${index + 1}
                                        </td>

                                        <td>
                                            ${escapeHtml(row.student_name)}
                                        </td>

                                        <td>
                                            ${row.grade}/${row.section}
                                        </td>

                                        <td>
                                            ${escapeHtml(row.father_phone || "-")}
                                        </td>

                                        <td>
                                            ${escapeHtml(row.father_phone_status)}
                                        </td>

                                        <td>
                                            ${escapeHtml(row.mother_phone || "-")}
                                        </td>

                                        <td>
                                            ${escapeHtml(row.mother_phone_status)}
                                        </td>

                                    </tr>
                                `
                            )
                            .join("")
                    }

                </tbody>

            </table>
        `;

    } catch (error) {

        container.innerHTML = `
            <div class="empty-state">
                تعذر تحميل البيانات.
            </div>
        `;

    }

}


/* =========================================================
   EXCEL STUDENT UPDATE
========================================================= */

async function previewStudentsExcel() {

    const input =
        document.getElementById(
            "studentsExcelFile"
        );

    const preview =
        document.getElementById(
            "excelImportPreview"
        );

    const btn =
        document.getElementById(
            "confirmExcelImportBtn"
        );

    btn.classList.add("hidden");

    if (!input.files.length) {

        showMessage(
            "اختاري ملف Excel أولًا.",
            "error"
        );

        return;
    }

    preview.innerHTML = `
        <div class="empty-state">
            جاري فحص الملف...
        </div>
    `;

    const form =
        new FormData();

    form.append(
        "file",
        input.files[0]
    );

    try {

        const response =
            await fetch(
                "/api/students/import-preview",
                {
                    method: "POST",
                    body: form
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {

            preview.innerHTML = `
                <div class="empty-state">
                    ${escapeHtml(
                        data.message ||
                        "تعذر فحص الملف."
                    )}
                </div>
            `;

            return;
        }

        let html = `
            <div class="management-result-item">

                <div>
                    <strong>
                        إجمالي صالح
                    </strong>
                    <small>
                        ${data.total_valid}
                    </small>
                </div>

                <div>
                    ➕ جديد:
                    <strong>
                        ${data.new_count}
                    </strong>
                </div>

                <div>
                    🔄 تحديث:
                    <strong>
                        ${data.update_count}
                    </strong>
                </div>

                <div>
                    ✅ بدون تغيير:
                    <strong>
                        ${data.unchanged_count}
                    </strong>
                </div>

                <div>
                    ⚠️ مراجعة:
                    <strong>
                        ${data.issue_count}
                    </strong>
                </div>

            </div>
        `;

        if (data.updates.length) {

            html +=
                "<h4>التغييرات المتوقعة</h4>" +

                data.updates
                    .slice(0, 30)
                    .map(
                        x => `
                            <div class="management-result-item">

                                <div>

                                    <strong>
                                        ${escapeHtml(x.student_name)}
                                    </strong>

                                    <small>
                                        ${escapeHtml(x.old_class)}
                                        ←
                                        ${escapeHtml(x.new_class)}
                                    </small>

                                </div>

                            </div>
                        `
                    )
                    .join("");

        }

        if (data.issues.length) {

            html +=
                "<h4>⚠️ تحتاج مراجعة</h4>" +

                data.issues
                    .slice(0, 30)
                    .map(
                        x => `
                            <div class="management-result-item">

                                <div>

                                    <strong>
                                        ${escapeHtml(x.student_name)}
                                    </strong>

                                    <small>
                                        السطر ${escapeHtml(x.row)}
                                        —
                                        ${escapeHtml(x.reason)}
                                    </small>

                                </div>

                            </div>
                        `
                    )
                    .join("");

        }

        preview.innerHTML =
            html;

        if (
            data.issue_count === 0
        ) {

            btn.classList.remove(
                "hidden"
            );

        }

    } catch (error) {

        preview.innerHTML = `
            <div class="empty-state">
                تعذر الاتصال بالنظام.
            </div>
        `;

    }

}


async function confirmStudentsExcelImport() {

    const input =
        document.getElementById(
            "studentsExcelFile"
        );

    if (!input.files.length) {
        return;
    }

    if (
        !confirm(
            "سيتم إضافة الجديد وتحديث الموجود مع الاحتفاظ بجميع سجلات الغياب السابقة. هل تريدين المتابعة؟"
        )
    ) {
        return;
    }

    const form =
        new FormData();

    form.append(
        "file",
        input.files[0]
    );

    try {

        const response =
            await fetch(
                "/api/students/import-confirm",
                {
                    method: "POST",
                    body: form
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {

            showMessage(
                data.message ||
                "تعذر التحديث.",
                "error"
            );

            return;
        }

        showMessage(
            data.message
        );

        document
            .getElementById(
                "confirmExcelImportBtn"
            )
            .classList
            .add("hidden");

        document.getElementById(
            "excelImportPreview"
        ).innerHTML = `
            <div class="empty-state">
                ✅ ${escapeHtml(data.message)}
            </div>
        `;

        await refreshAll();

    } catch (error) {

        showMessage(
            "تعذر تنفيذ تحديث Excel.",
            "error"
        );

    }

}


/* =========================================================
   SETTINGS
========================================================= */
async function loadSettings() {

    try {

        const response =
            await fetch(
                "/api/settings"
            );

        const data =
            await response.json();

        systemSettings = {
            ...systemSettings,
            ...data
        };

        if (
            document.getElementById(
                "settingSchoolName"
            )
        ) {
            document.getElementById(
                "settingSchoolName"
            ).value =
                data.school_name || "";
        }

        if (
            document.getElementById(
                "settingAcademicYear"
            )
        ) {
            document.getElementById(
                "settingAcademicYear"
            ).value =
                data.academic_year || "";
        }

        if (
            document.getElementById(
                "settingAlertLimit"
            )
        ) {
            document.getElementById(
                "settingAlertLimit"
            ).value =
                data.absence_alert_limit || 8;
        }

        if (
            document.getElementById(
                "settingDailyMessage"
            )
        ) {
            document.getElementById(
                "settingDailyMessage"
            ).value =
                data.daily_message || "";
        }

        if (
            document.getElementById(
                "settingAlertMessage"
            )
        ) {
            document.getElementById(
                "settingAlertMessage"
            ).value =
                data.alert_message || "";
        }

    } catch (error) {

        console.error(
            "Settings error:",
            error
        );

    }

}


async function saveSettings() {

    const payload = {
        school_name:
            document
                .getElementById(
                    "settingSchoolName"
                )
                .value
                .trim(),

        academic_year:
            document
                .getElementById(
                    "settingAcademicYear"
                )
                .value
                .trim(),

        absence_alert_limit:
            document
                .getElementById(
                    "settingAlertLimit"
                )
                .value,

        daily_message:
            document
                .getElementById(
                    "settingDailyMessage"
                )
                .value
                .trim(),

        alert_message:
            document
                .getElementById(
                    "settingAlertMessage"
                )
                .value
                .trim()
    };

    try {

        const response =
            await fetch(
                "/api/settings",
                {
                    method: "PUT",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            showMessage(
                data.message,
                "error"
            );

            return;
        }

        systemSettings = {
            ...systemSettings,
            ...payload
        };

        showMessage(
            data.message ||
            "تم حفظ الإعدادات بنجاح."
        );

        await refreshAll();

    } catch (error) {

        showMessage(
            "تعذر حفظ الإعدادات.",
            "error"
        );

    }

}


/* =========================================================
   BACKUP
========================================================= */

async function createBackup() {

    try {

        const response =
            await fetch(
                "/api/backup",
                {
                    method: "POST"
                }
            );

        if (!response.ok) {

            const data =
                await response.json();

            showMessage(
                data.message ||
                "تعذر إنشاء النسخة الاحتياطية.",
                "error"
            );

            return;
        }

        const blob =
            await response.blob();

        const disposition =
            response.headers.get(
                "Content-Disposition"
            );

        let filename =
            "attendance_backup.db";

        if (disposition) {

            const match =
                disposition.match(
                    /filename="?([^"]+)"?/
                );

            if (match) {
                filename = match[1];
            }

        }

        const url =
            URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        link.href = url;
        link.download = filename;

        document.body.appendChild(
            link
        );

        link.click();
        link.remove();

        URL.revokeObjectURL(url);

        showMessage(
            "تم إنشاء النسخة الاحتياطية."
        );

    } catch (error) {

        showMessage(
            "تعذر إنشاء النسخة الاحتياطية.",
            "error"
        );

    }

}


/* =========================================================
   MODALS
========================================================= */

function openModal(modalId) {

    const modal =
        document.getElementById(
            modalId
        );

    if (modal) {

        modal.classList.remove(
            "hidden"
        );

    }

}


function closeModal(modalId) {

    const modal =
        document.getElementById(
            modalId
        );

    if (modal) {

        modal.classList.add(
            "hidden"
        );

    }

}


function openMissingClassesModal() {

    renderMissingClasses();

    openModal(
        "missingClassesModal"
    );

}


/* =========================================================
   PHONE HELPERS
========================================================= */

function convertArabicDigits(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    const arabicDigits =
        "٠١٢٣٤٥٦٧٨٩";

    const persianDigits =
        "۰۱۲۳۴۵۶۷۸۹";

    return String(value)
        .replace(
            /[٠-٩]/g,
            digit =>
                arabicDigits.indexOf(
                    digit
                )
        )
        .replace(
            /[۰-۹]/g,
            digit =>
                persianDigits.indexOf(
                    digit
                )
        );

}


function normalizeLocalPhone(value) {

    let phone =
        convertArabicDigits(
            value
        )
            .replace(
                /\D/g,
                ""
            );

    if (!phone) {
        return "";
    }

    if (
        phone.startsWith("00968")
    ) {
        phone =
            phone.slice(5);
    }

    if (
        phone.startsWith("968") &&
        phone.length > 8
    ) {
        phone =
            phone.slice(3);
    }

    if (
        phone.length > 8
    ) {
        phone =
            phone.slice(-8);
    }

    return phone;

}


function normalizePhoneForWhatsApp(
    value
) {

    const local =
        normalizeLocalPhone(
            value
        );

    if (
        !local ||
        local.length !== 8
    ) {
        return "";
    }

    return "968" + local;

}


/* =========================================================
   DATE / TIME
========================================================= */

function formatTime(value) {

    if (!value) {
        return "-";
    }

    try {

        const date =
            new Date(value);

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {

            const parts =
                String(value)
                    .split(" ");

            if (
                parts.length > 1
            ) {

                return parts[1]
                    .slice(0, 5);

            }

            return value;
        }

        return date
            .toLocaleTimeString(
                "ar-OM",
                {
                    hour:
                        "2-digit",

                    minute:
                        "2-digit"
                }
            );

    } catch (error) {

        return value;

    }

}


/* =========================================================
   ESCAPE HELPERS
========================================================= */

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );

}


function escapeJs(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll(
            "\\",
            "\\\\"
        )
        .replaceAll(
            "'",
            "\\'"
        )
        .replaceAll(
            '"',
            '\\"'
        )
        .replaceAll(
            "\n",
            "\\n"
        )
        .replaceAll(
            "\r",
            "\\r"
        );

}