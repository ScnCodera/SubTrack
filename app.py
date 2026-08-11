import io
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dateutil.relativedelta import relativedelta

# ----------------------------------------------------------------------------
# Page setup
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="SubTrack | Subscription Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

CATEGORIES = [
    "Streaming",
    "Music",
    "Cloud Storage",
    "Software & SaaS",
    "Gaming",
    "News & Magazines",
    "Fitness",
    "Shopping & Delivery",
    "Productivity",
    "Other",
]

CYCLES = ["Weekly", "Monthly", "Quarterly", "Yearly"]
STATUSES = ["Active", "Paused", "Cancelled"]

CATEGORY_COLORS = {
    "Streaming": "#6C5CE7",
    "Music": "#00B894",
    "Cloud Storage": "#0984E3",
    "Software & SaaS": "#E17055",
    "Gaming": "#FD79A8",
    "News & Magazines": "#FDCB6E",
    "Fitness": "#00CEC9",
    "Shopping & Delivery": "#A29BFE",
    "Productivity": "#55EFC4",
    "Other": "#B2BEC3",
}

CYCLE_STEP = {
    "Weekly": relativedelta(weeks=1),
    "Monthly": relativedelta(months=1),
    "Quarterly": relativedelta(months=3),
    "Yearly": relativedelta(years=1),
}

CYCLE_MONTHLY_FACTOR = {
    "Weekly": 52 / 12,
    "Monthly": 1,
    "Quarterly": 1 / 3,
    "Yearly": 1 / 12,
}

SAMPLE_FILE = "sample_subscriptions.csv"


def inject_css():
    st.markdown(
        """
        <style>
        #MainMenu, footer {visibility: hidden;}

        html, body, [class*="css"] {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .stApp {
            background: linear-gradient(180deg, #F7F8FC 0%, #EFF1FA 100%);
        }

        .app-header {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 4px;
        }

        .app-header h1 {
            font-size: 2rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(90deg, #6C5CE7, #A29BFE);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .app-subtitle {
            color: #6B7280;
            font-size: 0.95rem;
            margin-bottom: 1.6rem;
        }

        .metric-card {
            background: #FFFFFF;
            border-radius: 18px;
            padding: 1.1rem 1.3rem;
            box-shadow: 0 6px 18px rgba(108, 92, 231, 0.08);
            border: 1px solid rgba(108, 92, 231, 0.08);
            height: 100%;
        }

        .metric-label {
            font-size: 0.82rem;
            color: #8A8FA3;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .metric-value {
            font-size: 1.7rem;
            font-weight: 800;
            color: #1E1E2E;
            margin-top: 2px;
        }

        .metric-icon {
            font-size: 1.4rem;
        }

        .metric-delta {
            font-size: 0.8rem;
            color: #00B894;
            margin-top: 4px;
        }

        .section-card {
            background: #FFFFFF;
            border-radius: 18px;
            padding: 1.4rem 1.5rem;
            box-shadow: 0 6px 18px rgba(108, 92, 231, 0.06);
            border: 1px solid rgba(108, 92, 231, 0.06);
            margin-bottom: 1.2rem;
        }

        .badge {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .badge-active { background: #E6FAF4; color: #00B894; }
        .badge-paused { background: #FFF6E0; color: #E1A100; }
        .badge-cancelled { background: #FDECEC; color: #E74C3C; }

        .urgent-row {
            border-left: 4px solid #E74C3C;
            padding-left: 10px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1E1E2E 0%, #2A2A3D 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #EDEDF7 !important;
        }
        section[data-testid="stSidebar"] .stRadio label {
            font-size: 0.95rem;
        }

        div[data-testid="stMetricValue"] {
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Data helpers
# ----------------------------------------------------------------------------
def load_sample_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(SAMPLE_FILE, parse_dates=["start_date"])
    except FileNotFoundError:
        df = pd.DataFrame(
            columns=["id", "name", "category", "cost", "billing_cycle", "start_date", "status", "notes"]
        )
    df["start_date"] = pd.to_datetime(df["start_date"]).dt.date
    return df


def next_renewal(start: date, cycle: str) -> date:
    step = CYCLE_STEP.get(cycle, relativedelta(months=1))
    today = date.today()
    renewal = start
    guard = 0
    while renewal < today and guard < 2000:
        renewal += step
        guard += 1
    return renewal


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.assign(monthly_cost=[], next_renewal=[], days_left=[])
    out = df.copy()
    out["monthly_cost"] = out.apply(
        lambda r: round(r["cost"] * CYCLE_MONTHLY_FACTOR.get(r["billing_cycle"], 1), 2), axis=1
    )
    out["next_renewal"] = out.apply(lambda r: next_renewal(r["start_date"], r["billing_cycle"]), axis=1)
    out["days_left"] = out["next_renewal"].apply(lambda d: (d - date.today()).days)
    return out


def new_id(df: pd.DataFrame) -> int:
    return int(df["id"].max()) + 1 if not df.empty else 1


def style_status(val: str) -> str:
    colors = {
        "Active": "background-color:#E6FAF4;color:#00B894;font-weight:700;",
        "Paused": "background-color:#FFF6E0;color:#E1A100;font-weight:700;",
        "Cancelled": "background-color:#FDECEC;color:#E74C3C;font-weight:700;",
    }
    return colors.get(val, "")


def metric_card(col, icon, label, value, sub=None):
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">{icon}</div>
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                {f'<div class="metric-delta">{sub}</div>' if sub else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
if "subs" not in st.session_state:
    st.session_state.subs = load_sample_data()
if "budget" not in st.session_state:
    st.session_state.budget = 6000


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
def sidebar_nav() -> str:
    with st.sidebar:
        st.markdown("## 💳 SubTrack")
        st.caption("Know where your money renews.")
        st.markdown("---")
        page = st.radio(
            "Navigate",
            ["🏠 Dashboard", "📋 My Subscriptions", "➕ Add Subscription", "📊 Insights & Forecast", "⚙️ Import / Export"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown("#### Monthly Budget Alert")
        st.session_state.budget = st.slider(
            "Alert me if spend exceeds (₹)", min_value=500, max_value=20000,
            value=int(st.session_state.budget), step=250,
        )
        st.markdown("---")
        st.caption(f"Tracking **{len(st.session_state.subs)}** subscriptions")
        st.caption("Built with Streamlit · Data stays in your session")
    return page


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_dashboard():
    st.markdown('<div class="app-header"><h1>Dashboard</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">A snapshot of everything you\'re paying for right now.</div>', unsafe_allow_html=True)

    df = enrich(st.session_state.subs)
    active = df[df["status"] == "Active"] if not df.empty else df

    monthly_spend = active["monthly_cost"].sum() if not active.empty else 0
    yearly_spend = monthly_spend * 12
    upcoming = active[active["days_left"].between(0, 7)] if not active.empty else active
    most_expensive = (
        active.sort_values("monthly_cost", ascending=False).iloc[0]["name"] if not active.empty else "—"
    )

    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "💰", "Monthly Spend", f"₹{monthly_spend:,.0f}")
    metric_card(c2, "📅", "Yearly Spend", f"₹{yearly_spend:,.0f}")
    metric_card(c3, "✅", "Active Subscriptions", f"{len(active)}")
    metric_card(c4, "⏰", "Renewing in 7 days", f"{len(upcoming)}")

    if monthly_spend > st.session_state.budget:
        st.error(
            f"⚠️ You're ₹{monthly_spend - st.session_state.budget:,.0f} over your ₹{st.session_state.budget:,.0f} monthly budget alert."
        )
    else:
        st.success(f"You're ₹{st.session_state.budget - monthly_spend:,.0f} under your monthly budget alert.")

    st.write("")
    left, right = st.columns([1.1, 1])

    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### Spend by Category")
        if not active.empty:
            cat_spend = active.groupby("category")["monthly_cost"].sum().reset_index()
            fig = px.pie(
                cat_spend, names="category", values="monthly_cost", hole=0.55,
                color="category", color_discrete_map=CATEGORY_COLORS,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active subscriptions yet. Add one to see the breakdown.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### Top 5 by Monthly Cost")
        if not active.empty:
            top5 = active.sort_values("monthly_cost", ascending=False).head(5)
            fig = px.bar(
                top5, x="monthly_cost", y="name", orientation="h", color="category",
                color_discrete_map=CATEGORY_COLORS, text="monthly_cost",
            )
            fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            fig.update_layout(
                yaxis=dict(autorange="reversed", title=""), xaxis_title="₹ / month",
                showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=320,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nothing to rank yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f"##### 🔔 Renewing Soon &nbsp; <span style='font-weight:400;color:#8A8FA3;font-size:0.85rem'>most expensive active plan: {most_expensive}</span>", unsafe_allow_html=True)
    soon = active[active["days_left"].between(0, 14)].sort_values("days_left") if not active.empty else active
    if soon.empty:
        st.info("Nothing renewing in the next two weeks.")
    else:
        for _, r in soon.iterrows():
            urgency = "🔴" if r["days_left"] <= 3 else "🟠" if r["days_left"] <= 7 else "🟡"
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].write(f"**{r['name']}**")
            cols[1].write(r["category"])
            cols[2].write(f"₹{r['cost']:,.0f} / {r['billing_cycle']}")
            cols[3].write(r["next_renewal"].strftime("%d %b %Y"))
            cols[4].write(f"{urgency} {r['days_left']}d")
    st.markdown("</div>", unsafe_allow_html=True)


def page_subscriptions():
    st.markdown('<div class="app-header"><h1>My Subscriptions</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Search, filter, and manage every subscription in one place.</div>', unsafe_allow_html=True)

    df = enrich(st.session_state.subs)

    with st.container():
        f1, f2, f3 = st.columns([2, 2, 2])
        search = f1.text_input("🔍 Search by name", "")
        cat_filter = f2.multiselect("Category", CATEGORIES)
        status_filter = f3.radio("Status", ["All"] + STATUSES, horizontal=True)

    view = df.copy()
    if search:
        view = view[view["name"].str.contains(search, case=False, na=False)]
    if cat_filter:
        view = view[view["category"].isin(cat_filter)]
    if status_filter != "All":
        view = view[view["status"] == status_filter]

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    if view.empty:
        st.info("No subscriptions match those filters.")
    else:
        display = view[["name", "category", "cost", "billing_cycle", "next_renewal", "days_left", "status"]].copy()
        display = display.rename(columns={
            "name": "Service", "category": "Category", "cost": "Cost", "billing_cycle": "Cycle",
            "next_renewal": "Next Renewal", "days_left": "Days Left", "status": "Status",
        })
        styled = display.style.map(style_status, subset=["Status"]).format({"Cost": "₹{:,.0f}"})
        st.dataframe(styled, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("✏️ Edit or remove subscriptions"):
        st.caption("Edit any cell inline, or use the row checkbox + delete icon to remove a subscription.")
        edited = st.data_editor(
            st.session_state.subs,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "category": st.column_config.SelectboxColumn("Category", options=CATEGORIES),
                "billing_cycle": st.column_config.SelectboxColumn("Billing Cycle", options=CYCLES),
                "status": st.column_config.SelectboxColumn("Status", options=STATUSES),
                "cost": st.column_config.NumberColumn("Cost (₹)", min_value=0.0, format="₹%.2f"),
                "start_date": st.column_config.DateColumn("Start Date"),
            },
            key="editor",
        )
        if st.button("💾 Save changes"):
            fixed = edited.reset_index(drop=True)
            next_available = new_id(st.session_state.subs)
            new_ids = []
            for val in fixed["id"]:
                if pd.isna(val):
                    new_ids.append(next_available)
                    next_available += 1
                else:
                    new_ids.append(int(val))
            fixed["id"] = new_ids
            st.session_state.subs = fixed
            st.success("Changes saved.")
            st.rerun()


def page_add():
    st.markdown('<div class="app-header"><h1>Add Subscription</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Track a new service in a few seconds.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    with st.form("add_subscription", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Service Name*", placeholder="e.g. Netflix")
            category = st.selectbox("Category", CATEGORIES)
            cost = st.number_input("Cost per billing cycle (₹)*", min_value=0.0, step=10.0)
        with c2:
            billing_cycle = st.selectbox("Billing Cycle", CYCLES)
            start_dt = st.date_input("Subscription Start Date", value=date.today())
            status = st.radio("Status", STATUSES, horizontal=True)
        notes = st.text_area("Notes (optional)", placeholder="Shared with family, work expense, etc.")
        submitted = st.form_submit_button("➕ Add Subscription", use_container_width=True)

        if submitted:
            if not name.strip():
                st.warning("Give the subscription a name before adding it.")
            elif cost <= 0:
                st.warning("Cost should be greater than ₹0.")
            else:
                row = pd.DataFrame([{
                    "id": new_id(st.session_state.subs), "name": name.strip(), "category": category,
                    "cost": cost, "billing_cycle": billing_cycle, "start_date": start_dt,
                    "status": status, "notes": notes,
                }])
                st.session_state.subs = pd.concat([st.session_state.subs, row], ignore_index=True)
                st.success(f"Added **{name}** to your subscriptions.")
    st.markdown("</div>", unsafe_allow_html=True)


def page_insights():
    st.markdown('<div class="app-header"><h1>Insights & Forecast</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Where the money goes, and where it\'s headed.</div>', unsafe_allow_html=True)

    df = enrich(st.session_state.subs)
    active = df[df["status"] == "Active"] if not df.empty else df

    tab1, tab2, tab3 = st.tabs(["📊 Spend Breakdown", "📈 12-Month Forecast", "🔔 Upcoming Renewals"])

    with tab1:
        if active.empty:
            st.info("Add some active subscriptions to see a breakdown.")
        else:
            cat_spend = active.groupby("category")["monthly_cost"].sum().sort_values(ascending=False).reset_index()
            fig = px.bar(
                cat_spend, x="category", y="monthly_cost", color="category",
                color_discrete_map=CATEGORY_COLORS, text="monthly_cost",
            )
            fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="₹ / month", height=380)
            st.plotly_chart(fig, use_container_width=True)

            cycle_mix = active["billing_cycle"].value_counts().reset_index()
            cycle_mix.columns = ["billing_cycle", "count"]
            fig2 = px.pie(cycle_mix, names="billing_cycle", values="count", hole=0.5)
            fig2.update_layout(height=320, margin=dict(t=10, b=10))
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        if active.empty:
            st.info("Nothing to forecast yet.")
        else:
            monthly_total = active["monthly_cost"].sum()
            months = pd.date_range(date.today().replace(day=1), periods=12, freq="MS")
            forecast = pd.DataFrame({
                "month": months.strftime("%b %Y"),
                "cumulative_spend": [monthly_total * (i + 1) for i in range(12)],
            })
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=forecast["month"], y=forecast["cumulative_spend"], mode="lines+markers",
                fill="tozeroy", line=dict(color="#6C5CE7", width=3),
            ))
            fig.update_layout(
                yaxis_title="Cumulative ₹ spent", xaxis_title="", height=380,
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Assumes today's {len(active)} active subscriptions renew on schedule with no changes — "
                f"roughly ₹{monthly_total * 12:,.0f} over the next 12 months."
            )

    with tab3:
        window = st.slider("Show renewals within the next N days", 1, 90, 30)
        upcoming = active[active["days_left"].between(0, window)].sort_values("days_left") if not active.empty else active
        if upcoming.empty:
            st.info(f"No renewals in the next {window} days.")
        else:
            table = upcoming[["name", "category", "cost", "billing_cycle", "next_renewal", "days_left"]].rename(
                columns={"name": "Service", "category": "Category", "cost": "Cost", "billing_cycle": "Cycle",
                         "next_renewal": "Renews On", "days_left": "Days Left"}
            )
            st.dataframe(table, use_container_width=True, hide_index=True)


def page_import_export():
    st.markdown('<div class="app-header"><h1>Import / Export</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Move your data in and out — nothing here is stored on a server.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### ⬆️ Import CSV")
        st.caption("Expected columns: id, name, category, cost, billing_cycle, start_date, status, notes")
        uploaded = st.file_uploader("Choose a CSV file", type="csv")
        mode = st.radio("On import", ["Replace current data", "Merge with current data"], horizontal=False)
        if uploaded is not None:
            try:
                new_df = pd.read_csv(uploaded, parse_dates=["start_date"])
                new_df["start_date"] = pd.to_datetime(new_df["start_date"]).dt.date
                if mode == "Replace current data":
                    st.session_state.subs = new_df
                else:
                    combined = pd.concat([st.session_state.subs, new_df], ignore_index=True)
                    combined["id"] = range(1, len(combined) + 1)
                    st.session_state.subs = combined
                st.success(f"Imported {len(new_df)} rows.")
            except Exception as e:
                st.error(f"Could not read that file: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### ⬇️ Export CSV")
        st.caption("Download your current subscription list.")
        buf = io.StringIO()
        st.session_state.subs.to_csv(buf, index=False)
        st.download_button(
            "Download subscriptions.csv", data=buf.getvalue(),
            file_name="subscriptions.csv", mime="text/csv", use_container_width=True,
        )
        st.write("")
        if st.button("↺ Reset to sample data", use_container_width=True):
            st.session_state.subs = load_sample_data()
            st.success("Reset to the sample dataset.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    inject_css()
    page = sidebar_nav()

    if page == "🏠 Dashboard":
        page_dashboard()
    elif page == "📋 My Subscriptions":
        page_subscriptions()
    elif page == "➕ Add Subscription":
        page_add()
    elif page == "📊 Insights & Forecast":
        page_insights()
    elif page == "⚙️ Import / Export":
        page_import_export()


if __name__ == "__main__":
    main()
