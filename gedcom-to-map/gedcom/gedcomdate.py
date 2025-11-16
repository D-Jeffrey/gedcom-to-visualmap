__all__ = ['CheckAge', 'DateFormatter']

import logging
from typing import Dict

from ged4py.date import DateValueVisitor
from models.Person import Person

_log = logging.getLogger(__name__.lower())

maxage = 122        # https://en.wikipedia.org/wiki/List_of_the_verified_oldest_people
maxmotherage = 66   # https://www.oldest.org/people/mothers/
maxfatherage = 93   # https://www.guinnessworldrecords.com/world-records/oldest-father-
minmother = 11
minfather = 12


def CheckAge(people: Dict[str, Person], thisXrefID ):
    ""
    problems :list[str] = []
    if people[thisXrefID]:
        thisperson = people[thisXrefID]
        born = None
        died = None
        if thisperson.birth:
            born = thisperson.birth.whenyearnum()
        if thisperson.death:
            died = thisperson.death.whenyearnum()
        if born and died:
            if died < born:
                problems.append("Died before Born")
            if died - born > maxage:
                problems.append(f"Too old {died - born} > {maxage}")
        if thisperson.children:
            for childId in thisperson.children:
                if people[childId]:
                    child = people[childId]
                    if child.birth and child.birth.whenyearnum():
                        if born:
                            parentatage = child.birth.whenyearnum() - born
                            if thisperson.sex == "F":
                                if parentatage > maxmotherage:
                                    problems.append(f"Mother too old {parentatage} > {maxmotherage} for {child.name} [{child.xref_id}]")
                                if parentatage < minmother:
                                    problems.append(f"Mother too young {parentatage} < {minmother} for {child.name} [{child.xref_id}]")
                             
                                if died and died < parentatage:
                                    problems.append(f"Mother after death for {child.name} [{child.xref_id}]")
                            elif thisperson.sex == "M":
                                if parentatage > maxfatherage:
                                    problems.append(f"Father too old {parentatage} > {maxfatherage} for {child.name} [{child.xref_id}]")
                                if parentatage < minfather:
                                    problems.append(f"Father too young {parentatage} < {minfather} for {child.name} [{child.xref_id}]")

                                # Birth after father dies within a year
                                if died and died+1 < parentatage:    
                                    problems.append(f"Father after death for {child.name} [{child.xref_id}]")
                            else:
                                if parentatage > max(maxfatherage,maxmotherage):
                                    problems.append(f"Parent too old {parentatage} > {max(maxfatherage,maxmotherage)} for {child.name} [{child.xref_id}]")
                                if parentatage < min(minmother, minfather):
                                    problems.append(f"Parent too young {parentatage} < {min(maxfatherage,maxmotherage)} for {child.name} [{child.xref_id}]")

    return problems

            

class DateFormatter(DateValueVisitor):
    """Visitor class that produces string representation of dates.
    """
    def visitSimple(self, date):
        return f"{date.date}"
    def visitPeriod(self, date):
        return f"from {date.date1} to {date.date2}"
    def visitFrom(self, date):
        return f"from {date.date}"
    def visitTo(self, date):
        return f"to {date.date}"
    def visitRange(self, date):
        return f"between {date.date1} and {date.date2}"
    def visitBefore(self, date):
        return f"before {date.date}"
    def visitAfter(self, date):
        return f"after {date.date}"
    def visitAbout(self, date):
        return f"about {date.date}"
    def visitCalculated(self, date):
        return f"calculated {date.date}"
    def visitEstimated(self, date):
        return f"estimated {date.date}"
    def visitInterpreted(self, date):
        return f"interpreted {date.date} ({date.phrase})"
    def visitPhrase(self, date):
        return f"({date.phrase})"
