import requests
from bs4 import BeautifulSoup

# Scrape UO business catalog for all undergraduate programs and their course requirements
#================================================================================================

# Step 1: Load the base business catalog page
base_url = "https://catalog.uoregon.edu/coll-business/#undergraduatetext"
headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(base_url, headers=headers)
soup = BeautifulSoup(response.content, "html.parser")

# Step 2: Extract all links to undergraduate majors/minors
program_links = []
# List of department paths to exclude
department_paths = [
    "/coll-business/accounting/",
    "/coll-business/finance/",
    "/coll-business/management/",
    "/coll-business/marketing/",
    "/coll-business/operations-business-analytics/"
]
for a in soup.select("a[href^='/coll-business/']"):
    href = a['href']
    # Skip concentrations, PDF links, and department pages
    if ("/ug-conc/" in href or 
        "coll-business.pdf" in href or 
        href in department_paths):
        continue
    title = a.get_text(strip=True)
    # Exclude doctoral programs
    if "PhD" in title:
        continue
    full_url = "https://catalog.uoregon.edu" + href
    program_links.append((title, full_url))

# Print out found program titles and links
for title, href in program_links:
    print(f"{title}: {href}")

def scrape_program_page(title, url):
    print(f"\nScraping {title}: {url}")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    # Step 2a: Scrape the program description (just below the page heading)
    description_container = soup.select("div#textcontainer p")
    description = "\n".join(p.get_text(strip=True) for p in description_container if p.get_text(strip=True))
    description = description.strip() if description else "No description found."

    print(f"\nDescription for {title}:\n{description}")

    # Step 2b: Go to the #requirementstext anchor
    requirements_url = url.split("#")[0] + "#requirementstext"
    req_response = requests.get(requirements_url, headers=headers)
    req_soup = BeautifulSoup(req_response.content, "html.parser")
    # Parse footnotes into a dictionary keyed by superscript number
    footnotes = {}
    for footnote_item in req_soup.select("dl.sc_footnotes"):
        dt_tags = footnote_item.select("dt")
        dd_tags = footnote_item.select("dd")
        for dt, dd in zip(dt_tags, dd_tags):
            key = dt.get_text(strip=True)
            value = dd.get_text(strip=True)
            footnotes[key] = value

    # Extract pre-major requirements text and split into two fields
    pre_major_paragraphs = req_soup.select("div#requirementstextcontainer > p")
    all_pre_major_text = "\n".join(p.get_text(strip=True) for p in pre_major_paragraphs if p.get_text(strip=True))

    # Split based on known boundary about international students requirement
    if "In addition, international students are required to take Academic English" in all_pre_major_text:
        split_point = all_pre_major_text.find("In addition, international students are required to take Academic English")
        pre_major_requirements = all_pre_major_text[:split_point].strip()

        # Add back the international student line
        remainder = all_pre_major_text[split_point:]
        first_para_end = remainder.find("\n")
        if first_para_end != -1:
            pre_major_requirements += "\n" + remainder[:first_para_end].strip()
            additional_program_info = remainder[first_para_end:].strip()
        else:
            pre_major_requirements += "\n" + remainder.strip()
            additional_program_info = ""
    else:
        pre_major_requirements = all_pre_major_text
        additional_program_info = ""

    # Append footnotes and UL content to additional_program_info
    footnote_block = req_soup.select("dl.sc_footnotes dd p")
    footnote_text = "\n".join(p.get_text(strip=True) for p in footnote_block if p.get_text(strip=True))
 
    list_items = req_soup.select("ul li.body")
    list_text = "\n".join(li.get_text(strip=True) for li in list_items if li.get_text(strip=True))
 
    if footnote_text:
        additional_program_info += ("\n\n" + footnote_text if additional_program_info else footnote_text)
    if list_text:
        additional_program_info += ("\n\n" + list_text if additional_program_info else list_text)
 
    # Step 2c: Extract the course requirement table
    courses = []
    for row in req_soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) >= 3:
            code_link = cols[0].find("a")
            code = (code_link.get_text(strip=True) if code_link else cols[0].get_text(strip=True)).replace('\xa0', ' ')
            credits = cols[2].get_text(strip=True)
            course_url_tag = cols[0].find("a")
            course_url = (
                "https://catalog.uoregon.edu" + course_url_tag["href"]
                if course_url_tag
                else None
            )
            course_data = {
                "code": code,
                "credits": credits,
                "course_url": course_url
            }

            if course_url:
                course_details = scrape_course_details(course_url)
                course_data.update(course_details)
                courses.append(course_data)
    # Deduplicate courses by 'code'
    unique_courses = {}
    for course in courses:
        code = course["code"]
        if code not in unique_courses:
            unique_courses[code] = course
    courses = list(unique_courses.values())

    print(f"\nFound {len(courses)} required courses for {title}. Example:")
    if courses:
        print(courses[0])

    # Extract grouped tables and section headers for degree_path
    degree_path = []
    tables = req_soup.select("div#requirementstextcontainer table.sc_courselist")
    for table in tables:
        # Find the previous heading (e.g., "Core Courses")
        heading_tag = table.find_previous(["h3", "h4", "strong"])
        section_title = heading_tag.get_text(strip=True) if heading_tag else "Unnamed Section"
        section_footnote = None
        if heading_tag and heading_tag.find("sup"):
            sup = heading_tag.find("sup").get_text(strip=True)
            section_footnote = footnotes.get(sup.strip())
        sub_section_labels = []
        section_courses = []
        current_group = []
        rows = table.select("tr")
 
        for i, row in enumerate(rows):
            if "areaheader" in row.get("class", []):
                span = row.select_one("span.courselistcomment.areaheader")
                if span:
                    label = span.get_text(strip=True)
                    sub_section_labels.append((label, len(section_courses)))
                continue
 
            cols = row.find_all("td")
            if len(cols) == 3 and "orclass" not in row.get("class", []):
                if current_group:
                    section_courses.append(current_group)
                    current_group = []
 
                code_link = cols[0].select_one("a")
                code = code_link.get_text(strip=True).replace("\xa0", " ") if code_link else cols[0].get_text(strip=True).replace("\xa0", " ")
                credits = cols[2].get_text(strip=True)
                current_group = [{
                    "options": [code],
                    "credits": credits
                }]
            elif "orclass" in row.get("class", []):
                code_cell = row.select_one("td.codecol")
                if code_cell:
                    code_link = code_cell.select_one("a")
                    code = code_link.get_text(strip=True).replace("\xa0", " ") if code_link else code_cell.get_text(strip=True).replace("\xa0", " ")
                    if current_group:
                        current_group[0]["options"].append(code)
 
        if current_group:
            section_courses.append(current_group[0])
 
        if section_courses:
            if sub_section_labels:
                subsections = []
                for idx, (label, start_index) in enumerate(sub_section_labels):
                    end_index = sub_section_labels[idx + 1][1] if idx + 1 < len(sub_section_labels) else len(section_courses)
                    subsections.append({
                        "subsection": label,
                        "requirements": section_courses[start_index:end_index]
                    })
                entry = {
                    "section": section_title,
                    "subsections": subsections
                }
                if section_footnote:
                    entry["footnote"] = section_footnote
                degree_path.append(entry)
            else:
                entry = {
                    "section": section_title,
                    "subsections": [{
                        "subsection": "",
                        "requirements": section_courses
                    }]
                }
                if section_footnote:
                    entry["footnote"] = section_footnote
                degree_path.append(entry)

    return {
        "program": title,
        "description": description,
        "pre_major_requirements": pre_major_requirements,
        "additional_program_info": additional_program_info,
        "courses": courses,
        "degree_path": degree_path,
    }

# Example: scrape just the Accounting program
accounting_url = next(url for title, url in program_links if "Accounting" in title)

def scrape_course_details(url):
    if not url:
        return {}

    print(f"Scraping course: {url}")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract heading like "BA 101Z. Introduction to Business. 4 Credits."
    heading_tag = soup.select_one("div.searchresult.search-courseresult h2")
    if heading_tag:
        heading_text = heading_tag.get_text(strip=True)
        parts = heading_text.split(".")
        if len(parts) >= 2:
            code = parts[0].strip().replace('\xa0', ' ')
            title = parts[1].strip()
        else:
            code = ""
            title = ""
    else:
        code = ""
        title = ""

    # Description paragraph
    course_info = soup.select_one("p.courseblockdesc")
    course_details = course_info.get_text(strip=True) if course_info else "No course description found."

    # Extract and separate structured metadata from description
    requisites = ""
    equivalent_to = ""
    additional_info = ""

    if "Additional Information:" in course_details:
        parts = course_details.split("Additional Information:")
        course_details = parts[0].strip()
        additional_info = parts[1].strip()

    if "Requisites:Prereq:" in course_details:
        parts = course_details.split("Requisites:Prereq:")
        course_details = parts[0].strip()
        rest = parts[1]
        if "Equivalent to:" in rest:
            req_parts = rest.split("Equivalent to:")
            requisites = req_parts[0].strip()
            equivalent_to = req_parts[1].strip()
        else:
            requisites = rest.strip()
    elif "Equivalent to:" in course_details:
        parts = course_details.split("Equivalent to:")
        course_details = parts[0].strip()
        equivalent_to = parts[1].strip()

    # Check for standing requirements in course_details
    for standing in ["Sophomore standing required", "Junior standing required", "Senior standing required"]:
        if standing in course_details:
            requisites = (requisites + " " + standing).strip()
            course_details = course_details.replace(standing, "").strip()

    # The old 'extra_info' field remains in case the page has it in a different div
    metadata_block = soup.select_one("div.courseblockextra")
    metadata_text = metadata_block.get_text(strip=True) if metadata_block else ""

    return {
        "code": code,
        "title": title,
        "description": course_details,
        "requisites": requisites,
        "equivalent_to": equivalent_to,
        "additional_info": additional_info,
        "extra_info": metadata_text
    }

import json
import os

base_output_dir = "/Users/alexanderrankine/Desktop/RAGappAttempt1/data/business_catalog"

for title, url in program_links:
    try:
        # Determine category based on the program title
        if "Minor" in title:
            category = os.path.join("undergraduate", "minors")
        elif "Certificate" in title:
            category = os.path.join("undergraduate", "certificates")
        elif any(keyword in title for keyword in ["MBA", "MS", "MACC", "MActg", "(MAcctg)", "MAcc", "Master of Accounting"]):
            category = "masters"
        else:
            category = os.path.join("undergraduate", "majors")

        output_dir = os.path.join(base_output_dir, category)
        os.makedirs(output_dir, exist_ok=True)

        data = scrape_program_page(title, url)
        filename = title.lower().replace(" ", "_").replace("/", "-") + ".json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filepath}")
    except Exception as e:
        print(f"Error processing {title}: {e}")
