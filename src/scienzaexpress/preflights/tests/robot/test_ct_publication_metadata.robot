# ============================================================================
# DEXTERITY ROBOT TESTS
# ============================================================================
#
# Run this robot test stand-alone:
#
#  $ bin/test -s scienzaexpress.preflights -t test_publication_metadata.robot --all
#
# Run this robot test with robot server (which is faster):
#
# 1) Start robot server:
#
# $ bin/robot-server --reload-path src scienzaexpress.preflights.testing.SCIENZAEXPRESS_PREFLIGHTS_ACCEPTANCE_TESTING
#
# 2) Run robot tests:
#
# $ bin/robot /src/scienzaexpress/preflights/tests/robot/test_publication_metadata.robot
#
# See the http://docs.plone.org for further details (search for robot
# framework).
#
# ============================================================================

*** Settings *****************************************************************

Resource  plone/app/robotframework/selenium.robot
Resource  plone/app/robotframework/keywords.robot

Library  Remote  ${PLONE_URL}/RobotRemote

Test Setup  Open test browser
Test Teardown  Close all browsers


*** Test Cases ***************************************************************

Scenario: As a site administrator I can add a Publication Metadata
  Given a logged-in site administrator
    and an add Publication Metadata form
   When I type 'My Publication Metadata' into the title field
    and I submit the form
   Then a Publication Metadata with the title 'My Publication Metadata' has been created

Scenario: As a site administrator I can view a Publication Metadata
  Given a logged-in site administrator
    and a Publication Metadata 'My Publication Metadata'
   When I go to the Publication Metadata view
   Then I can see the Publication Metadata title 'My Publication Metadata'


*** Keywords *****************************************************************

# --- Given ------------------------------------------------------------------

a logged-in site administrator
  Enable autologin as  Site Administrator

an add Publication Metadata form
  Go To  ${PLONE_URL}/++add++Publication Metadata

a Publication Metadata 'My Publication Metadata'
  Create content  type=Publication Metadata  id=my-publication_metadata  title=My Publication Metadata

# --- WHEN -------------------------------------------------------------------

I type '${title}' into the title field
  Input Text  name=form.widgets.IBasic.title  ${title}

I submit the form
  Click Button  Save

I go to the Publication Metadata view
  Go To  ${PLONE_URL}/my-publication_metadata
  Wait until page contains  Site Map


# --- THEN -------------------------------------------------------------------

a Publication Metadata with the title '${title}' has been created
  Wait until page contains  Site Map
  Page should contain  ${title}
  Page should contain  Item created

I can see the Publication Metadata title '${title}'
  Wait until page contains  Site Map
  Page should contain  ${title}
