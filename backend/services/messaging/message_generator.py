"""
Generates personalized outreach messages using connection properties
(name, title, company, degree, mutual connections). No AI or external APIs used.
"""


def _template_message(user: dict, target_person: dict, target_company: str, context: dict) -> str:
    """Generate a personalized message using the person's name, role, and company."""
    name = target_person.get("name", "").split()[0]  # First name
    title = target_person.get("title", "")
    degree = target_person.get("degree", 1)
    is_recruiter = target_person.get("is_recruiter", False)
    bridge = context.get("bridge_person")
    sender = user.get("name", "")

    if is_recruiter:
        return (
            f"Hi {name},\n\n"
            f"I came across your profile and saw you're recruiting at {target_company}. "
            f"I'm really interested in the work being done there"
            f"{' and ' + bridge.get('name','') + ' suggested I reach out' if bridge else ''}. "
            f"Would you be open to a quick coffee chat sometime?\n\n"
            f"Best,\n{sender}"
        )
    elif degree == 2 and bridge:
        bridge_name = bridge.get("name", "our mutual connection").split()[0]
        return (
            f"Hi {name},\n\n"
            f"I noticed we're connected through {bridge_name}, "
            f"and I've been really impressed by the {title} work at {target_company}. "
            f"I'd love to learn more about your experience there. "
            f"Would you be open to a quick coffee chat?\n\n"
            f"Best,\n{sender}"
        )
    else:
        return (
            f"Hi {name},\n\n"
            f"Great to connect! I've been following what {target_company} is building "
            f"and your work as {title} really caught my eye. "
            f"I'd love to hear about your experience there. "
            f"Would you be open to grabbing a coffee chat sometime?\n\n"
            f"Best,\n{sender}"
        )


async def generate_outreach_message(
    user: dict,
    target_person: dict,
    target_company: str,
    context: dict
) -> str:
    return _template_message(user, target_person, target_company, context)
