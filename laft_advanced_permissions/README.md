# Laft Advanced Permissions System

## نظام الصلاحيات المتقدم لشركة لفت

نظام احترافي ومبسط لإدارة صلاحيات المستخدمين في Odoo.

---

## ✨ المزايا الرئيسية

### 🎯 **واجهة مبسطة**
- Checkboxes سهلة بدلاً من Groups معقدة
- تطبيق تلقائي للصلاحيات
- قوالب جاهزة للأدوار الشائعة

### 🏗️ **المشاريع**
- **User**: مشاريعه فقط (Own Projects Only)
- **Manager**: إدارة كاملة لمشاريعه
- **Finance**: Manager + Bills/POs
- **General Manager**: رؤية **كل** المشاريع

### 💼 **تطوير الأعمال**
- **User**: فرصه فقط
- **Manager**: فرص الفريق
- **Executive**: كل الفرص

### 📊 **Dashboard**
- نظرة شاملة على الصلاحيات
- من هو Admin/Manager؟
- Quick Links للفئات

---

## 📋 **كيفية الاستخدام**

### 1️⃣ **إضافة مستخدم جديد**

```
Settings → Users & Companies → Permission Management → Users
```

1. اضغط **Create**
2. املأ البيانات الأساسية (Name, Email, Login)
3. اذهب لتاب **📋 Permissions**
4. اختر:
   - **Projects Access**: Manager - Own Projects
   - ☑ Can Create Projects
   - ☑ Can View Vendor Bills
5. اضغط **Save**

✅ تلقائياً يحصل على الصلاحيات المناسبة!

---

### 2️⃣ **استخدام Role Templates**

```
Settings → Permission Management → Role Templates
```

القوالب الجاهزة:
- 👤 Project User
- 👔 Project Manager
- 💰 Project Manager + Finance
- 👑 General Project Manager
- 💼 BD User
- 💼 BD Manager
- 👑 BD Executive
- 🎯 Project & BD Manager (Combined)

---

### 3️⃣ **عرض من لديه صلاحيات معينة**

```
Settings → Permission Management → Quick Links
```

- 👑 **Administrators**: كل الـ Admins
- 🏗️ **Project Managers**: كل مديري المشاريع
- 💼 **BD Team**: كل فريق تطوير الأعمال

---

## 🔒 **الصلاحيات بالتفصيل**

### **المشاريع:**

| المستوى | ماذا يرى؟ | ماذا يستطيع؟ |
|---------|-----------|--------------|
| User | مشاريعه فقط | عرض + مهامه |
| Manager | مشاريعه فقط | إنشاء + إدارة كاملة |
| Finance | مشاريعه فقط | Manager + Bills/POs |
| General | **كل** المشاريع | كل شيء |

### **Record Rules:**

```python
# Manager - Own Projects Only:
[('user_id', '=', user.id)]

# General Manager - See All:
[(1, '=', 1)]
```

### **Vendor Bills:**

```python
# Project Manager يرى فقط:
[
    ('move_type', '=', 'in_invoice'),
    ('project_id.user_id', '=', user.id)
]

# Customer Invoices ممنوعة:
[('move_type', '!=', 'out_invoice')]
```

---

## 🎛️ **الإعدادات المتقدمة**

### **Override: See All Projects**

checkbox منفصل يسمح برؤية **كل** المشاريع بغض النظر عن المستوى:

```
☑ Override: See All Projects
```

### **Finance Access Levels:**

- **None**: لا وصول
- **Project-Related Only**: فقط Bills/POs المرتبطة بمشاريعه
- **Invoicing**: وصول كامل للفواتير
- **Accounting**: وصول كامل للمحاسبة

---

## 🔧 **للمطورين**

### **Structure:**

```
laft_advanced_permissions/
├── models/
│   ├── res_users.py           # User extensions
│   └── laft_permission_role.py # Role templates
├── security/
│   ├── laft_security_groups.xml
│   ├── project_security_rules.xml
│   ├── bd_security_rules.xml
│   └── finance_security_rules.xml
├── views/
│   ├── res_users_permission_views.xml
│   ├── permission_dashboard_views.xml
│   └── laft_permission_role_views.xml
└── data/
    └── default_roles_data.xml
```

### **Key Models:**

**res.users:**
- `laft_project_access`: Selection
- `laft_bd_access`: Selection  
- `laft_finance_access`: Selection
- Auto-applies groups on change

**laft.permission.role:**
- Pre-configured role templates
- Can be applied to multiple users

### **Groups Created:**

```xml
<!-- Project -->
group_project_user_own
group_project_manager_own
group_project_manager_finance
group_project_general_manager

<!-- BD -->
group_bd_user_own
group_bd_manager_team
group_bd_executive

<!-- Permission -->
group_permission_manager
```

---

## 📞 **الدعم**

لأي استفسارات أو مشاكل، تواصل مع الفريق التقني.

---

**Developed with ❤️ by Laft Company**

