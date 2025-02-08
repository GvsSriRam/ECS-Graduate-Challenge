import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://ecs.syracuse.edu/faculty-staff?category=full-time-fac&people="

def scrape_directory(directory_url):
    """
    Scrape the main faculty/staff directory page to get profile URLs.
    """
    response = requests.get(directory_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    # The directory page contains profile cards in divs with class "ecs-profile"
    cards = soup.find_all("div", class_="ecs-profile")
    
    profile_urls = []
    for card in cards:
        # The name and link are in the <div class="profile-name"> element
        name_div = card.find("div", class_="profile-name")
        if name_div:
            a_tag = name_div.find("a")
            if a_tag and a_tag.get("href"):
                profile_url = a_tag["href"]
                # Ensure absolute URL
                if profile_url.startswith("/"):
                    profile_url = BASE_URL + profile_url
                profile_urls.append(profile_url)
    return profile_urls

def scrape_profile(profile_url):
    """
    Scrape a single professor's detail page and extract key fields.
    """
    response = requests.get(profile_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    profile_data = {}
    
    # Name from <h1 class="title">
    name_tag = soup.find("h1", class_="title")
    profile_data["name"] = name_tag.get_text(strip=True) if name_tag else "N/A"
    
    # Positions, typically in the first <h3> inside the entry content
    h3_tag = soup.find("h3")
    profile_data["positions"] = h3_tag.get_text(separator=" ", strip=True) if h3_tag else "N/A"
    
    # Extract h4 details: department, location, email, phone.
    # The first h4 with class "profile-department-meta" is assumed to be department.
    h4_tags = soup.find_all("h4")
    department = None
    location = None
    email = None
    phone = None
    for tag in h4_tags:
        classes = tag.get("class", [])
        text = tag.get_text(strip=True)
        if "profile-department-meta" in classes:
            department = text
        elif "@" in text:
            email = text
        elif any(ch.isdigit() for ch in text) and len(text) < 20:
            phone = text
        else:
            # If not department, email, or phone, then assume location (if not already set)
            if not location:
                location = text
    profile_data["department"] = department if department else "N/A"
    profile_data["location"] = location if location else "N/A"
    profile_data["email"] = email if email else "N/A"
    profile_data["phone"] = phone if phone else "N/A"
    
    # Helper function: given a heading text, find the following <ul> and return list items.
    def extract_list_after_heading(heading_text):
        result = []
        heading_p = soup.find("p", text=lambda t: t and heading_text in t)
        if heading_p:
            ul = heading_p.find_next_sibling("ul")
            if ul:
                for li in ul.find_all("li"):
                    result.append(li.get_text(strip=True))
        return result
    
    # Degrees (look for a paragraph with "Degrees:")
    profile_data["degrees"] = extract_list_after_heading("Degrees:")
    
    # Areas of Expertise (look for a paragraph with "Areas of Expertise:")
    profile_data["areas_of_expertise"] = extract_list_after_heading("Areas of Expertise:")
    
    # Honors and Awards (look for a paragraph with "Honors and Awards:")
    profile_data["honors_and_awards"] = extract_list_after_heading("Honors and Awards:")
    
    # Selected Publications (look for a paragraph with "Selected Publications:")
    profile_data["selected_publications"] = extract_list_after_heading("Selected Publications:")
    
    # For Biography, try to grab the first non-heading <p> in the entry content.
    bio_paragraphs = []
    for p in soup.find_all("p"):
        # Skip <p> tags that have a <strong> (likely headings)
        if p.find("strong") is None:
            text = p.get_text(strip=True)
            if text:
                bio_paragraphs.append(text)
    # Pick the first paragraph as the biography, if available.
    profile_data["biography"] = bio_paragraphs[0] if bio_paragraphs else "N/A"
    
    return profile_data

def scrape_all_profiles(directory_url):
    """
    Scrape all professor profiles starting from the directory page.
    """
    all_profiles = []
    profile_urls = scrape_directory(directory_url)
    print(f"Found {len(profile_urls)} profiles.")
    
    for url in profile_urls:
        print(f"Scraping {url}")
        try:
            profile_data = scrape_profile(url)
            all_profiles.append(profile_data)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        # Pause to be polite to the server
        time.sleep(1)
    return all_profiles

def save_profiles_to_csv(profiles, filename):
    """
    Save the list of profile dictionaries to a CSV file.
    """
    # Determine CSV columns based on keys from the first profile
    if not profiles:
        return
    fieldnames = list(profiles[0].keys())
    
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for profile in profiles:
            writer.writerow(profile)

if __name__ == "__main__":
    directory_url = "https://ecs.syracuse.edu/faculty-staff"
    profiles = scrape_all_profiles(directory_url)
    
    # Print out each profile's name
    for prof in profiles:
        print(f"{prof['name']}: {prof['email']}")
    
    # Save to CSV
    save_profiles_to_csv(profiles, "ecs_faculty_profiles.csv")
