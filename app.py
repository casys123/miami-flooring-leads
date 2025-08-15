# app.py
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import datetime
import base64

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import io
import base64

# Initialize session state
if 'leads' not in st.session_state:
    st.session_state.leads = pd.DataFrame(columns=['Company', 'Website', 'Email', 'Phone', 'Source'])
if 'campaigns' not in st.session_state:
    st.session_state.campaigns = {}

# Page config
st.set_page_config(page_title="Miami Flooring Lead Generator", layout="wide")
st.title("🚀 Miami Master Flooring - Lead Generation System")

# Sidebar for credentials
with st.sidebar:
    st.header("API Configuration")
    serpapi_key = st.text_input("SerpAPI Key", type="password")
    email_user = st.text_input("Email User", "contact@miamimasterflooring.com")
    email_pass = st.text_input("Email Password", type="password")
    
    st.divider()
    st.image("https://i.imgur.com/7zB9QgW.png", width=150)
    st.caption("Miami Master Flooring Prospector v1.0")

# Search function
def search_companies(query, engine):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    results = []
    
    if engine == "google":
        url = f"https://www.google.com/search?q={query}&num=20"
    elif engine == "bing":
        url = f"https://www.bing.com/search?q={query}&count=20"
    else:
        return results
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if engine == "google":
            for g in soup.find_all('div', class_='tF2Cxc'):
                link = g.find('a')['href']
                title = g.find('h3').text
                results.append({"title": title, "link": link})
        elif engine == "bing":
            for item in soup.find_all('li', class_='b_algo'):
                link = item.find('a')['href']
                title = item.find('h2').text
                results.append({"title": title, "link": link})
    except Exception as e:
        st.error(f"Error searching {engine}: {str(e)}")
    
    return results

# Email extraction function
def extract_emails(url):
    try:
        response = requests.get(url, timeout=10)
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', response.text)
        return list(set(emails))
    except:
        return []

# Company info extraction
def extract_company_info(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Attempt to find company name
        name = ""
        possible_selectors = [
            'h1', 'div.logo', 'meta[property="og:title"]', 
            'meta[property="og:site_name"]', 'title'
        ]
        for selector in possible_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text().strip() or element.get('content', '')
                if name: break
        
        # Attempt to find phone number
        phone = ""
        phone_pattern = re.compile(r'\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
        phone_match = phone_pattern.search(response.text)
        if phone_match:
            phone = phone_match.group()
        
        return name, phone
    except:
        return "", ""

# Email template
def create_email_template(company_name, sender_name="Alex", sender_title="Business Development Manager"):
    return f"""Subject: Premium Flooring Solutions for Your Projects - Miami Master Flooring

Dear {company_name or 'Construction Professional'},

I noticed your exceptional work in the construction industry through our market research. At Miami Master Flooring, we specialize in high-end flooring installations for commercial and residential projects across South Florida.

Our services include:
- Luxury vinyl plank (LVP) installations
- Waterproof flooring solutions
- Custom tile and stone work
- 10-year craftsmanship warranty

We'd appreciate the opportunity to discuss how we can support your upcoming projects with our premium materials and skilled installation teams.

When might be convenient for a brief call next week?

Best regards,
{sender_name}
{sender_title}
Miami Master Flooring
📞 (305) 555-7890
🌐 www.miamimasterflooring.com

[Unsubscribe]"""

# Main app
tab1, tab2, tab3 = st.tabs(["🔍 Find Companies", "✉️ Create Campaign", "📊 Analytics"])

with tab1:
    st.subheader("Find Construction Companies")
    col1, col2 = st.columns(2)
    
    with col1:
        query = st.text_input("Search Query", "flooring contractors in Miami")
        search_engines = st.multiselect("Search Engines", ["google", "bing"], ["google"])
        
    with col2:
        max_results = st.slider("Max Results", 10, 100, 30)
        include_competitors = st.checkbox("Include competitors? (Not recommended)", False)
    
    if st.button("Start Search", type="primary"):
        if not query:
            st.warning("Please enter a search query")
        else:
            with st.spinner("Searching construction companies..."):
                all_results = []
                
                for engine in search_engines:
                    engine_results = search_companies(query, engine)
                    for result in engine_results[:max_results]:
                        result['source'] = engine
                        all_results.append(result)
                
                if not all_results:
                    st.error("No results found. Try different search terms.")
                else:
                    results_df = pd.DataFrame(all_results)
                    st.success(f"Found {len(results_df)} company websites")
                    
                    # Process results
                    progress_bar = st.progress(0)
                    for i, row in enumerate(results_df.itertuples()):
                        try:
                            # Extract company info
                            name, phone = extract_company_info(row.link)
                            
                            # Extract emails
                            emails = extract_emails(row.link)
                            valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg'))]
                            
                            # Filter out competitors
                            if not include_competitors and any(kw in name.lower() for kw in ['floor', 'tile', 'carpet']):
                                continue
                            
                            # Add to leads
                            if valid_emails:
                                new_lead = {
                                    'Company': name,
                                    'Website': row.link,
                                    'Email': valid_emails[0],
                                    'Phone': phone,
                                    'Source': row.source
                                }
                                st.session_state.leads = pd.concat([
                                    st.session_state.leads, 
                                    pd.DataFrame([new_lead])
                                ], ignore_index=True)
                            
                        except Exception as e:
                            st.error(f"Error processing {row.link}: {str(e)}")
                        
                        progress_bar.progress((i+1)/len(results_df))
                    
                    st.success(f"Added {len(st.session_state.leads)} valid leads!")
    
    # Display results
    if not st.session_state.leads.empty:
        st.subheader("Extracted Leads")
        st.dataframe(st.session_state.leads)
        
        # Export to CSV
        csv = st.session_state.leads.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        st.download_button(
            label="Download Leads as CSV",
            data=csv,
            file_name='miami_flooring_leads.csv',
            mime='text/csv'
        )

with tab2:
    st.subheader("Email Campaign Management")
    
    if st.session_state.leads.empty:
        st.warning("No leads available. Find companies first.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            campaign_name = st.text_input("Campaign Name", "Q3-Flooring-Promotion")
            sender_name = st.text_input("Sender Name", "Alex Johnson")
            sender_title = st.text_input("Sender Title", "Business Development Manager")
            
            st.subheader("Email Template")
            template = st.text_area("Email Content", 
                                value=create_email_template("[Company Name]", sender_name, sender_title),
                                height=300)
        
        with col2:
            st.subheader("Scheduling")
            start_date = st.date_input("Start Date", datetime.date.today())
            time_between = st.slider("Days Between Emails", 1, 7, 3)
            emails_per_day = st.slider("Emails Per Day", 1, 100, 25)
            
            selected_leads = st.multiselect(
                "Select Leads to Include",
                options=st.session_state.leads['Company'],
                default=st.session_state.leads['Company'].tolist()
            )
            
            if st.button("Schedule Campaign", type="primary"):
                if not campaign_name:
                    st.warning("Please name your campaign")
                else:
                    campaign = {
                        'name': campaign_name,
                        'template': template,
                        'start_date': start_date,
                        'schedule': {
                            'time_between': time_between,
                            'emails_per_day': emails_per_day
                        },
                        'leads': selected_leads,
                        'status': 'Scheduled'
                    }
                    st.session_state.campaigns[campaign_name] = campaign
                    st.success(f"Campaign '{campaign_name}' scheduled!")
    
    # Campaign management
    if st.session_state.campaigns:
        st.subheader("Active Campaigns")
        for name, campaign in st.session_state.campaigns.items():
            with st.expander(f"{name} - {campaign['status']}"):
                st.write(f"**Start Date:** {campaign['start_date']}")
                st.write(f"**Emails per day:** {campaign['schedule']['emails_per_day']}")
                st.write(f"**Days between batches:** {campaign['schedule']['time_between']}")
                
                if st.button(f"Send Test Email - {name}"):
                    # This would actually send an email in production
                    st.info("Test email sent successfully!")
                
                if st.button(f"Execute Campaign - {name}"):
                    with st.spinner(f"Sending emails for {name}..."):
                        # This is where actual email sending would happen
                        time.sleep(2)  # Simulate sending
                        st.session_state.campaigns[name]['status'] = 'Completed'
                        st.experimental_rerun()

with tab3:
    st.subheader("Performance Analytics")
    
    if not st.session_state.campaigns:
        st.info("No campaigns run yet")
    else:
        st.metric("Total Leads", len(st.session_state.leads))
        
        campaign_data = []
        for name, campaign in st.session_state.campaigns.items():
            campaign_data.append({
                'Campaign': name,
                'Status': campaign['status'],
                'Leads': len(campaign['leads']),
                'Start Date': campaign['start_date']
            })
        
        st.dataframe(pd.DataFrame(campaign_data))
        
        # Simulated metrics
        st.subheader("Engagement Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Open Rate", "42%", "12%")
        col2.metric("Reply Rate", "8%", "3%")
        col3.metric("Conversion Rate", "3%", "1.2%")
        
        st.bar_chart(pd.DataFrame({
            'Opens': [120, 145, 132],
            'Replies': [28, 32, 41],
            'Dates': ['Aug 10', 'Aug 11', 'Aug 12']
        }).set_index('Dates'))

# Footer
st.divider()
st.caption("© 2023 Miami Master Flooring | This tool is for business development purposes only. Ensure compliance with all applicable laws including CAN-SPAM.")# ... [Insert the full code from previous response here] ...
