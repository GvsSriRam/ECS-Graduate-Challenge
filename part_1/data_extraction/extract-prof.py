import requests
from bs4 import BeautifulSoup
import csv

def scrape_ecs_faculty(url):
    # Fetch the page content
    response = requests.get(url)
    response.raise_for_status()  # Ensure the request was successful

    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find all profile cards by looking for divs with class "ecs-profile"
    faculty_cards = soup.find_all("div", class_="ecs-profile")
    faculty_list = []
    
    for card in faculty_cards:
        # Extract the name from the <div class="profile-name"> element,
        # specifically from the <a> tag inside it
        name_div = card.find("div", class_="profile-name")
        if name_div:
            a_tag = name_div.find("a")
            name = a_tag.get_text(strip=True) if a_tag else name_div.get_text(strip=True)
        else:
            name = "No Name Found"
        
        # # Extract the profile title from <div class="profile-title">
        # title_div = card.find("div", class_="profile-tit
        # le")
        # title = title_div.get_text(strip=True) if title_div else "No Title Found"
        
        # Optionally, extract the profile link from the <a> tag if available
        profile_link = a_tag["href"] if a_tag and a_tag.has_attr("href") else "No Link"
        
        faculty_list.append({
            "name": name,
            # "title": title,
            "profile_link": profile_link
        })
    
    return faculty_list

def save_to_csv(data, filename):
    # Save the scraped data to a CSV file
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "profile_link"])
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    url = "https://ecs.syracuse.edu/faculty-staff?category=full-time-fac&people="
    faculty_data = scrape_ecs_faculty(url)
    
    # Print the data
    for prof in faculty_data:
        print(f"{prof['name']} - {prof['profile_link']}")
    
    # Save the data to a CSV file
    save_to_csv(faculty_data, "ecs_faculty_staff.csv")
