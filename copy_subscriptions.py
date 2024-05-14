"""
Copy subscriptions from one stripe account to another
"""
import datetime

import stripe

# Settings for script

source = "YOUR_SOURCE_ACCOUNT_STRIPE_KEY"
dest = "YOUR_DESTINATION_ACCOUNT_STRIPE_KEY"

PRICES_IDS = {
    # "{OLD_PRICE_ID}": "{NEW_PRICE_ID}"
}


def update_db(dest_customer, dest_subscription):
    # if you need to update your database, you'll need to
    # add a database update method here. In my case, I'm using MongoDB

    # db_customer = db.users.find_one({"email": dest_customer.email})
    # if not db_customer:
    #     print(
    #         "Something went wrong. Customer", dest_customer.email, "not found in db"
    #     )
    #
    # if not dest_customer.email:
    #     print("Customer does not have email, will try to update by stripeId")
    #     db.users.update(
    #         {"stripeId": dest_customer.id},
    #         {
    #             "$set": {
    #                 "stripeId": dest_customer.id,
    #                 "subscriptionId": dest_subscription.id,
    #                 "hasSubscription": True,
    #             }
    #         },
    #         multi=True,
    #     )
    # else:
    #     db.users.update(
    #         {"email": dest_customer.email},
    #         {
    #             "$set": {
    #                 "stripeId": dest_customer.id,
    #                 "subscriptionId": dest_subscription.id,
    #                 "hasSubscription": True,
    #             }
    #         },
    #         multi=True,
    #     )
    # print(dest_customer.email, "updated in database")

    pass


def time_str(timestamp):
    """
    Convert timestamp to human-readable time.
    :param timestamp: timestamp
    :return: formatted time
    """
    return datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")


old_customers = stripe.Customer.list(limit=100, api_key=source)

while old_customers:
    for src_customer in old_customers.data:
        print("------------------------")
        print()

        if not src_customer.subscriptions.data:
            # if no subscriptions, just skip this customer
            print(
                "No subscriptions found for:",
                src_customer.email,
                src_customer.id,
                "- skipping.",
            )
            continue
        print("Customer on source account is:", src_customer.email, src_customer.id)

        dest_customer = stripe.Customer.retrieve(src_customer.id, api_key=dest)

        # if the customer already has a subscription
        # don't need to do anything
        if dest_customer.subscriptions.total_count >= 1:
            print(
                "New subscription already created for",
                dest_customer.email,
                ", skipping. Although you might want to check the database.",
            )
            continue

        # Get the subscription details
        subscriptions = src_customer.subscriptions.data
        for subscription in subscriptions:
            price = subscription.price.id
            subscription_end_date = subscription.current_period_end

            if subscription.cancel_at_period_end:
                print("skip customer:", src_customer.email, "already cancelled.")
                continue

            print()
            print("Product on source account:", price.product)
            print("Plan on source account ends on:", time_str(subscription_end_date))
            print("Original subscription id:", subscription.id)
            print()

            # your unique plan names here
            new_price = PRICES_IDS.get(price.id)

            if not new_price:
                print("No corresponding price found for:", price)
                continue

            if not subscription_end_date:
                print("Plan end date not found for:", src_customer.id)
                continue

            print()
            print(
                "Now copying to dest customer:", dest_customer.email, dest_customer.id
            )
            print("New price is:", new_price)
            print(
                "New subscription trial period ends:", time_str(subscription_end_date)
            )
            print()

            # create the subscription for the new customer
            dest_subscription = stripe.Subscription.create(
                customer=dest_customer.id,
                items=[{"price": new_price}],
                trial_end=subscription_end_date,
                api_key=dest,
            )

            print()
            print("New subscription created:", dest_subscription.id)
            print("New subscription type:", dest_subscription.plan.nickname)
            print("New subscription start:", time_str(dest_subscription.start))
            print()

            # update the database
            update_db(dest_customer, dest_subscription)

            # finally, cancel the subscription on the source stripe account
            old_sub = stripe.Subscription.retrieve(subscription.id, api_key=source)
            old_sub.delete(at_period_end=True)

            print("Old subscription,", subscription.id, "was cancelled. Next!")

        old_customers = stripe.Customer.list(
            limit=100, api_key=source, starting_after=src_customer.id
        )
