# ============================================================================
# DEXTERITY ROBOT TESTS
# ============================================================================
#
# Run this robot test stand-alone:
#
#  $ bin/test -s scienzaexpress.preflights -t test_metadata.robot --all
#
# Run this robot test with robot server (which is faster):
#
# 1) Start robot server:
#
# $ bin/robot-server --reload-path src scienzaexpress.preflights.testing.SCIENZAEXPRESS_PREFLIGHTS_ACCEPTANCE_TESTING
#
# 2) Run robot tests:
#
# $ bin/robot /src/scienzaexpress/preflights/tests/robot/test_metadata.robot
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

Scenario: As a site administrator I can add a Metadata
  Given a logged-in site administrator
    and an add Metadata form
   When I type 'My Metadata' into the title field
    and I submit the form
   Then a Metadata with the title 'My Metadata' has been created

Scenario: As a site administrator I can view a Metadata
  Given a logged-in site administrator
    and a Metadata 'My Metadata'
   When I go to the Metadata view
   Then I can see the Metadata title 'My Metadata'


*** Keywords *****************************************************************

# --- Given ------------------------------------------------------------------

a logged-in site administrator
  Enable autologin as  Site Administrator

an add Metadata form
  Go To  ${PLONE_URL}/++add++Metadata

a Metadata 'My Metadata'
  Create content  type=Metadata  id=my-metadata  title=My Metadata

# --- WHEN -------------------------------------------------------------------

I type '${title}' into the title field
  Input Text  name=form.widgets.IBasic.title  ${title}

I submit the form
  Click Button  Save

I go to the Metadata view
  Go To  ${PLONE_URL}/my-metadata
  Wait until page contains  Site Map


# --- THEN -------------------------------------------------------------------

a Metadata with the title '${title}' has been created
  Wait until page contains  Site Map
  Page should contain  ${title}
  Page should contain  Item created

I can see the Metadata title '${title}'
  Wait until page contains  Site Map
  Page should contain  ${title}
