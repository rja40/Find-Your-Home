package proj756
import scala.concurrent.duration._

import io.gatling.core.Predef._
import io.gatling.http.Predef._

class PositiveTestSimulationLandlord extends Simulation {
    val httpProtocol = http
        .baseUrl("http://" + Utility.envVar("CLUSTER_IP", "127.0.0.1") + "/")
        .acceptHeader("application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        .authorizationHeader("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiZGJmYmMxYzAtMDc4My00ZWQ3LTlkNzgtMDhhYTRhMGNkYTAyIiwidGltZSI6MTYwNzM2NTU0NC42NzIwNTIxfQ.zL4i58j62q8mGUo5a0SQ7MHfukBUel8yl8jGT5XmBPo")
        .acceptLanguageHeader("en-US,en;q=0.5")

    
    object landlord {
        val landlord = exec(
        http("Creating a landlord account")
            .post("/api/v1/landlord")
            .formParam("username", "testman1")
            .formParam("password", "donut")
            // .formParam("fname", "John") 
            .formParam("lname", "Doe")
            .formParam("email", "sjdoe@sfu.ca")
            .formParam("contact", 1415151)
        )
        .pause(1)
        .exec(
        http("Landlord login")
            .put("/api/v1/landlord/login")
            .formParam("username", "L_testman1") 
            // .formParam("password", "donut")
        )
        .pause(1)
        .exec(
        http("Property Creation by Landlord")
            .put("/api/v1/landlord/property")
            .formParam("street_address", "13618, 100 Ave") 
            .formParam("city", "Surrey")
            .formParam("pincode", "V3T0A8")
            // .formParam("availability", false)
            .formParam("beds", 2)
            .formParam("baths", 2)
            .formParam("rent", 1850)
            .formParam("facilities", "[WiFi, Heating, Hydro]")
        )
        .pause(1)
    }

  val scn = scenario("Employee search") // A scenario is a chain of requests and pauses
    .exec(landlord.landlord)
    .pause(1) // Note that Gatling has recorded real time pauses

  setUp(scn.inject(atOnceUsers(1)).protocols(httpProtocol))
}

class PositiveTestSimulationTenant extends Simulation {
    val httpProtocol = http
        .baseUrl("http://" + Utility.envVar("CLUSTER_IP", "127.0.0.1") + "/")
        .acceptHeader("application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        .authorizationHeader("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiZGJmYmMxYzAtMDc4My00ZWQ3LTlkNzgtMDhhYTRhMGNkYTAyIiwidGltZSI6MTYwNzM2NTU0NC42NzIwNTIxfQ.zL4i58j62q8mGUo5a0SQ7MHfukBUel8yl8jGT5XmBPo")
        .acceptLanguageHeader("en-US,en;q=0.5")

    object tenant {
        val tenant = exec(
        http("Creating a tenant account")
            .post("/api/v1/tenant")
            .formParam("username", "testman1")
            .formParam("password", "donut")
            .formParam("fname", "John") 
            .formParam("lname", "Doe")
            .formParam("email", "sjdoe@sfu.ca")
            .formParam("contact", 1415151)
        )
        .pause(1)
        .exec(
        http("Tenant login")
            .put("/api/v1/tenant/login")
            .formParam("username", "testman1") 
            .formParam("password", "donut")
        )
        .pause(1)
    }


  val scn = scenario("Employee search") // A scenario is a chain of requests and pauses
    .exec(tenant.tenant)
    .pause(1) // Note that Gatling has recorded real time pauses

  setUp(scn.inject(atOnceUsers(1)).protocols(httpProtocol))
}
